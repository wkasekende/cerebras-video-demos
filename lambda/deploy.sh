#!/usr/bin/env bash
# ── PACKAGE AND DEPLOY THE RENDER FUNCTION ───────────────────────────────────
#   bash lambda/deploy.sh
#
# Idempotent: creates the role, the bucket and the function when missing,
# updates the code when not. The zip carries handler.cjs, demokit-render.cjs,
# puppeteer-core, @sparticuz/chromium (x86_64) and a static ffmpeg
# (downloaded once, cached in lambda/bin, gitignored). A zip function, no
# docker. Knobs, all environment:
#
#   DEMOKIT_LAMBDA_FN       function name          (demokit-render)
#   DEMOKIT_LAMBDA_REGION   region                 (us-east-1)
#   DEMOKIT_LAMBDA_ROLE     execution role name    (demokit-render-lambda)
#   DEMOKIT_LAMBDA_ARCH     x86_64 | arm64         (x86_64). arm64 has no
#                        sparticuz build: set DEMOKIT_CHROME_S3 to a tarball
#                        (s3://bucket/key) holding chrome-linux/chrome, its
#                        lib/ closure, an ffmpeg and a fontconfig with at
#                        least one real font - Chromium paints invisible
#                        text from an empty fontconfig.
#   DEMOKIT_LAMBDA_BUCKET   S3 bucket for the zip  (demokit-render-deploy-<account id>)
#   AWS_CLI              the aws binary         (aws)
#
# agent-film.mjs --engine lambda reads DEMOKIT_LAMBDA_FN / DEMOKIT_LAMBDA_REGION the
# same way, so a deploy under other names is a render under other names.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS="${AWS_CLI:-aws}"
REGION="${DEMOKIT_LAMBDA_REGION:-us-east-1}"
ARCH="${DEMOKIT_LAMBDA_ARCH:-x86_64}"
FN="${DEMOKIT_LAMBDA_FN:-demokit-render}"
ROLE="${DEMOKIT_LAMBDA_ROLE:-demokit-render-lambda}"

if [ "$ARCH" != arm64 ] && [ ! -f "$DIR/bin/ffmpeg" ]; then
  echo "▸ fetching static ffmpeg (cached in lambda/bin, gitignored)"
  curl -sSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg-static.tar.xz
  tar -xf /tmp/ffmpeg-static.tar.xz -C /tmp
  mkdir -p "$DIR/bin"; cp /tmp/ffmpeg-*-amd64-static/ffmpeg "$DIR/bin/ffmpeg"
fi
if [ "$ARCH" = arm64 ] && [ -z "${DEMOKIT_CHROME_S3:-}" ]; then
  echo "arm64 needs DEMOKIT_CHROME_S3 (a chromium tarball on S3); see the header"; exit 1
fi

echo "▸ installing the function's dependencies"
if [ "$ARCH" = arm64 ]; then
  STAGE=$(mktemp -d)
  cp "$DIR/handler.cjs" "$DIR/demokit-render.cjs" "$STAGE/"
  printf '{ "name": "demokit-render", "private": true, "dependencies": { "puppeteer-core": "25.1.0" } }\n' > "$STAGE/package.json"
  ( cd "$STAGE" && npm install --omit=dev --no-audit --no-fund >/dev/null 2>&1 )
  PKDIR="$STAGE"; PARTS="handler.cjs demokit-render.cjs package.json node_modules"
else
  ( cd "$DIR" && npm install --omit=dev --no-audit --no-fund >/dev/null )
  PKDIR="$DIR"; PARTS="handler.cjs demokit-render.cjs bin node_modules package.json"
fi

ZIP=/tmp/demokit-render-lambda.zip
rm -f "$ZIP"
# python's zipfile, not zip(1): it lets the exec bit ride external_attr so
# bin/ffmpeg stays executable in /var/task, and every machine has python3
( cd "$PKDIR" && python3 - "$ZIP" $PARTS <<'PY'
import os, sys, zipfile
zf = zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED)
for root in sys.argv[2:]:
    paths = [root] if os.path.isfile(root) else \
        [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]
    for p in paths:
        zi = zipfile.ZipInfo(p)
        zi.external_attr = (os.stat(p).st_mode & 0xFFFF) << 16
        zi.compress_type = zipfile.ZIP_DEFLATED
        with open(p, 'rb') as f:
            zf.writestr(zi, f.read())
zf.close()
PY
)
echo "▸ zip $(du -m "$ZIP" | cut -f1)MB"

ACCT=$("$AWS" sts get-caller-identity --query Account --output text)
if ! "$AWS" iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  echo "▸ creating role $ROLE"
  "$AWS" iam create-role --role-name "$ROLE" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  "$AWS" iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  if [ -n "${DEMOKIT_CHROME_S3:-}" ]; then
    "$AWS" iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
  fi
  sleep 10   # IAM propagation
fi
ROLE_ARN="arn:aws:iam::$ACCT:role/$ROLE"

BUCKET="${DEMOKIT_LAMBDA_BUCKET:-demokit-render-deploy-$ACCT}"
"$AWS" s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null || \
  "$AWS" s3 mb "s3://$BUCKET" --region "$REGION" >/dev/null
"$AWS" s3 cp "$ZIP" "s3://$BUCKET/demokit-render-$ARCH.zip" --region "$REGION" --no-progress >/dev/null
# the function may read files the renderer stages in this bucket under assets/ (an agent film's pop-in frames ride there, not in the 6 MB invoke payload)
"$AWS" iam put-role-policy --role-name "$ROLE" --policy-name demokit-render-assets --policy-document \
  "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$BUCKET/assets/*\"}]}"

ENVVARS="DEMOKIT_LAMBDA_ARCH=$ARCH"
[ -n "${DEMOKIT_CHROME_S3:-}" ] && ENVVARS="$ENVVARS,DEMOKIT_CHROME_S3=$DEMOKIT_CHROME_S3"
if "$AWS" lambda get-function --function-name "$FN" --region "$REGION" >/dev/null 2>&1; then
  echo "▸ updating $FN"
  "$AWS" lambda update-function-code --function-name "$FN" --region "$REGION" \
    --s3-bucket "$BUCKET" --s3-key "demokit-render-$ARCH.zip" >/dev/null
else
  echo "▸ creating $FN (10240MB / 6 vCPU, 300s, 10GB /tmp, $ARCH)"
  "$AWS" lambda create-function --function-name "$FN" --region "$REGION" \
    --runtime nodejs22.x --handler handler.handler --role "$ROLE_ARN" \
    --code "S3Bucket=$BUCKET,S3Key=demokit-render-$ARCH.zip" \
    --memory-size 10240 --timeout 300 --ephemeral-storage Size=10240 \
    --architectures "$ARCH" --environment "Variables={$ENVVARS}" >/dev/null
fi
"$AWS" lambda wait function-updated-v2 --function-name "$FN" --region "$REGION" 2>/dev/null || \
  "$AWS" lambda wait function-active-v2 --function-name "$FN" --region "$REGION"
"$AWS" lambda update-function-configuration --function-name "$FN" --region "$REGION" \
  --environment "Variables={$ENVVARS}" --ephemeral-storage Size=10240 >/dev/null
"$AWS" lambda wait function-updated-v2 --function-name "$FN" --region "$REGION"
echo "deployed: $FN in $REGION  (render with: DEMOKIT_LAMBDA_FN=$FN DEMOKIT_LAMBDA_REGION=$REGION node tools/agent-film.mjs <cfg> --mp4 --engine lambda --segments 4)"
