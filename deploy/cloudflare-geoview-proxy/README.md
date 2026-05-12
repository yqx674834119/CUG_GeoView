# GeoView CUGxxx External Proxy

This deploys a free Cloudflare Workers reverse proxy.

Public path:

```text
https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/
```

Origin:

```text
https://livablecitylab.hkust-gz.edu.cn/Geoview/
```

Deploy:

```bash
cd /home/livablecity/GeoView/deploy/cloudflare-geoview-proxy
npm install
npx wrangler login
npx wrangler deploy
```

Test after deploy:

```bash
curl -I https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/
curl https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/health
curl https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/runtime-config.js
```

Notes:

- This is a real reverse proxy and streams request bodies, so normal upload/download requests do not need base64 wrapping.
- The user-facing URL does not expose `livablecitylab.hkust-gz.edu.cn`.
- Mainland China performance is not guaranteed on the free `workers.dev` domain. For stable China-friendly access, the practical free option is still to use an existing China-accessible domain or a domestic CDN account with a bound domain.
