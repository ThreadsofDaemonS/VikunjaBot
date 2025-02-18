# VikunjaBot
Bot for selecting and moving tasks across columns


1. Clone repository:
   ```bash
   git clone <repository_url>
   cd VikunjaBot
    ```
   
2. create venv:
   ```
   python -m venv .venv
   ```

3. ```
   pip install -r requirements.txt
   ```

4. Need ngrok for local webhook look in google how to install it

5. ```bash
   ngrok http 8000
    ```

6. Run:
```
python run.py
```
For making serever with webhook you need self-signed certificate
example for it is runwithwebhook.py

7. For webhook on the server you need this command
```bash
   openssl req -newkey rsa:2048 -sha256 -nodes -keyout webhook.key -x509 -days 365 -out webhook.pem

 ```
add in your .env with your certificate

WEBHOOK_SSL_CERT_PATH

WEBHOOK_SSL_PRIV_PATH

for example:
WEBHOOK_SSL_CERT = "/etc/ssl/certs/webhook.pem"
WEBHOOK_SSL_PRIV = "/etc/ssl/private/webhook.key"

Maybe you will need this, but it already in runwithwebhook.py:

curl -F "url=https://yourdomain.com:8443/PROJECT_NAME" \
     -F "certificate=@/etc/ssl/certs/webhook.pem" \
     "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"

This links can be useful for webhooks:

https://github.com/Marat2010/Aiogram3/tree/master
https://docs.aiogram.dev/en/latest/dispatcher/webhook.html

