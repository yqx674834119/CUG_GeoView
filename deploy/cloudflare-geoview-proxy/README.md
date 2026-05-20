# GeoView CUGxxx Redirect

This deploys a small Cloudflare Worker that redirects the public URL to the
original GeoView site.

Public path:

```text
https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/
```

Origin:

```text
https://livablecitylab.hkust-gz.edu.cn/GeoView
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
curl -I "https://cuggeoview.<your-cloudflare-subdomain>.workers.dev/CUGGeoView/?x=1"
```

Notes:

- This is only a redirect. The browser will leave the `workers.dev` URL and load
  `livablecitylab.hkust-gz.edu.cn` directly.
- Paths and query strings under `/CUGGeoView/` are preserved, for example
  `/CUGGeoView/api/system/ping?x=1` redirects to `/GeoView/api/system/ping?x=1`.
- A redirect avoids Cloudflare Worker proxy overhead, but it does not accelerate
  the origin site after the browser lands on `livablecitylab.hkust-gz.edu.cn`.
