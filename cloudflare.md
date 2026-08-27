# Cloudflare deployment guide

## 1. Cloudflare DNS
- Create a DNS record for your domain, for example: `shop.example.com` -> `your-render-or-vps-ip`
- Enable proxied mode if using Cloudflare proxy.

## 2. Backend behind Cloudflare
- Point `shop.example.com` to the backend app or reverse proxy.
- If you use a VPS/Nginx, configure upstream to `127.0.0.1:8000`.
- Keep Telegram webhook secret enabled.

## 3. Frontend hosting
- Put the static frontend behind Cloudflare Pages or your Nginx static root.
- Set `API_BASE` inside the frontend to the backend URL.

## 4. Security
- Force HTTPS only.
- Set `CORS_ORIGINS` to your frontend domain.
- Keep `WEBHOOK_SECRET` non-empty and strong.

## 5. Example Nginx snippet
```
server {
    listen 80;
    server_name shop.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Telegram webhook example
```
python -m bot.set_webhook https://shop.example.com/telegram/webhook
```

This gives a production-grade HTTPS layer in front of the app and keeps the bot secure.
