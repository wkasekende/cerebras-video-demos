# Security

This repository is a video-making kit that runs on your machine. It sends nothing anywhere unless you run the optional cloud renderer (`lambda/`), which uses your own AWS account and credentials.

- **Never put an API key, token or personal data in a storyboard or run log.** The builder refuses text shaped like a key, but it cannot catch everything. Look at your recording before you share a film.
- **Do not commit your AWS credentials.** `lambda/deploy.sh` reads them from your environment.
- **Reporting a problem:** open a private security advisory on the repository (Security tab, "Report a vulnerability"), or an issue if nothing sensitive is involved.
