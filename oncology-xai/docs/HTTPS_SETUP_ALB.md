# HTTPS Setup for LCHAI v2.0 on AWS ALB

**Domain:** `lchai.gptfy.biz`  
**DNS Provider:** Hostinger  
**AWS Region:** `us-east-1`  
**ALB Address:** `k8s-default-lchaiing-ac1c805be9-594537839.us-east-1.elb.amazonaws.com`

---

## Architecture

```
User Browser
    │
    ▼ HTTPS :443
AWS Application Load Balancer (ALB)
    │  ← SSL termination here (ACM certificate)
    ▼ HTTP (internal)
EKS Kubernetes Pods
    ├── webapp :3000        (path: /*)
    ├── api-gateway :8000   (path: /api/v1/*)
    └── keycloak :8080      (path: /auth/*)
```

SSL terminates at the ALB. Pods receive plain HTTP. No Nginx, Certbot, or Let's Encrypt is needed.

---

## Step 1 — Verify DNS CNAME for the domain

In **Hostinger DNS Zone** for `gptfy.biz`, confirm this CNAME exists:

| Type | Name | Target |
|------|------|--------|
| CNAME | `lchai` | `k8s-default-lchaiing-ac1c805be9-594537839.us-east-1.elb.amazonaws.com` |

**Verify:**
```bash
nslookup lchai.gptfy.biz
# Should resolve to the ALB address
```

---

## Step 2 — Check ACM certificate status

```bash
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:632100838024:certificate/0b8be42a-de6d-4296-ad66-7ded2bf1c263" \
  --region us-east-1 \
  --query "Certificate.{Status:Status,Domain:DomainName,ValidationMethod:DomainValidationOptions[0].ValidationMethod}" \
  --output table
```

Expected: `Status: PENDING_VALIDATION` (before DNS validation) or `Status: ISSUED` (after).

---

## Step 3 — Add DNS validation CNAME in Hostinger

The ACM certificate requires a CNAME record to prove domain ownership.

### CNAME to add in Hostinger DNS Zone for `gptfy.biz`:

| Type | Name (Host) | Target (Points to) | TTL |
|------|-------------|---------------------|-----|
| CNAME | `_3a1684def09da29d98087d0260dd3f9a.lchai` | `_d700c1768387dc6258c6d06c17ea933b.jkddzztszm.acm-validations.aws.` | 14400 |

### How to add in Hostinger:
1. Log in to **Hostinger** → **hPanel**
2. Go to **Domains** → select `gptfy.biz` → **DNS / Nameservers** → **DNS Records**
3. Click **Add Record**
4. Type: **CNAME**
5. Name (Host): `_3a1684def09da29d98087d0260dd3f9a.lchai`
   - Hostinger auto-appends `.gptfy.biz` — do NOT include it
6. Target (Points to): `_d700c1768387dc6258c6d06c17ea933b.jkddzztszm.acm-validations.aws.`
   - Include the trailing dot if Hostinger allows it
7. TTL: `14400` (or minimum available)
8. Click **Add Record**

### Verify DNS propagation:
```bash
nslookup _3a1684def09da29d98087d0260dd3f9a.lchai.gptfy.biz
# Should resolve to: _d700c1768387dc6258c6d06c17ea933b.jkddzztszm.acm-validations.aws
```

Or use: https://toolbox.googleapps.com/apps/dig/#CNAME/_3a1684def09da29d98087d0260dd3f9a.lchai.gptfy.biz

### Wait for ACM validation:
- Typically **5-30 minutes** after DNS propagates
- Check status:
```bash
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:632100838024:certificate/0b8be42a-de6d-4296-ad66-7ded2bf1c263" \
  --region us-east-1 \
  --query "Certificate.Status" \
  --output text
```
- Must return: `ISSUED`

---

## Step 4 — Update ALB Ingress for HTTPS

Once the certificate status is `ISSUED`, update the Kubernetes ingress.

### Option A: Via Helm (recommended)

Edit `infra/helm/lchai/templates/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lchai-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:us-east-1:632100838024:certificate/0b8be42a-de6d-4296-ad66-7ded2bf1c263"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
  rules:
    - host: lchai.gptfy.biz
      http:
        paths:
          - path: /api/v1
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 8000
          - path: /auth
            pathType: Prefix
            backend:
              service:
                name: keycloak
                port:
                  number: 8080
          - path: /
            pathType: Prefix
            backend:
              service:
                name: webapp
                port:
                  number: 3000
```

Then deploy:
```bash
helm upgrade lchai ./infra/helm/lchai \
  --set "postgres.password=<DB_PASSWORD>" \
  --set "openaiApiKey=<OPENAI_KEY>"
```

### Option B: Via AWS Console (manual)

1. Go to **AWS Console** → **EC2** → **Load Balancers**
2. Find the ALB: `k8s-default-lchaiing-ac1c805be9`
3. Click **Listeners** tab

#### Add HTTPS:443 listener:
4. Click **Add listener**
5. Protocol: **HTTPS**, Port: **443**
6. Default action: **Forward to** → select the webapp target group
7. Security policy: `ELBSecurityPolicy-TLS13-1-2-2021-06` (recommended)
8. Default SSL certificate: select `lchai.gptfy.biz` from ACM
9. Click **Add**

#### Add rules to HTTPS:443:
10. Click on the **HTTPS:443** listener → **View/edit rules**
11. Add rules matching the existing HTTP:80 rules:
    - **Rule 1**: IF Host = `lchai.gptfy.biz` AND Path = `/api/v1*` → Forward to `apigateway` target group
    - **Rule 2**: IF Host = `lchai.gptfy.biz` AND Path = `/auth*` → Forward to `keycloak` target group
    - **Default**: Forward to `webapp` target group

#### Configure HTTP:80 redirect:
12. Go back to **Listeners** → select **HTTP:80**
13. Edit the default action → change to **Redirect to HTTPS:443**
    - Protocol: HTTPS
    - Port: 443
    - Status code: 301

---

## Step 5 — Verify HTTPS is working

### DNS check:
```bash
nslookup lchai.gptfy.biz
# Should resolve to ALB address
```

### Certificate check:
```bash
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:632100838024:certificate/0b8be42a-de6d-4296-ad66-7ded2bf1c263" \
  --region us-east-1 \
  --query "Certificate.Status" --output text
# Must return: ISSUED
```

### HTTPS test:
```bash
curl -I https://lchai.gptfy.biz
# Expected: HTTP/2 200 (or 301/302 redirect to Keycloak login)
```

### HTTP redirect test:
```bash
curl -I http://lchai.gptfy.biz
# Expected: HTTP/1.1 301 Moved Permanently
# Location: https://lchai.gptfy.biz:443/
```

### Browser test:
1. Open `https://lchai.gptfy.biz` in Chrome
2. Should see Keycloak login page (or LCHAI webapp)
3. Padlock icon should be green/locked
4. Click padlock → certificate should show "Amazon" as issuer

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Certificate stuck at `PENDING_VALIDATION` | CNAME not added or wrong value | Double-check CNAME in Hostinger. Use Google DNS checker. Allow 30 min. |
| `UnsupportedCertificate` error | Certificate not yet `ISSUED` | Wait for ACM validation to complete |
| `502 Bad Gateway` | Target group health checks failing | Check health check path in ALB target group settings. Webapp uses `/`, api uses `/metrics` |
| `504 Gateway Timeout` | Pod not responding in time | Increase ALB idle timeout (default 60s) |
| Redirect loop (ERR_TOO_MANY_REDIRECTS) | App internally forces HTTPS | Pods must accept plain HTTP — they don't know about SSL |
| Keycloak login redirect fails | Keycloak configured with wrong base URL | Set `KC_PROXY=edge` and `KC_HOSTNAME_STRICT=false` in Keycloak env |
| CORS errors on API calls | Frontend uses HTTP but API is HTTPS | Update `VITE_API_URL` to `https://lchai.gptfy.biz` |
| Certificate expires | ACM auto-renews if DNS validation CNAME stays | Do NOT delete the validation CNAME from Hostinger |

---

## Summary of DNS records needed in Hostinger for `gptfy.biz`

| Type | Name | Target | Purpose |
|------|------|--------|---------|
| CNAME | `lchai` | `k8s-default-lchaiing-ac1c805be9-594537839.us-east-1.elb.amazonaws.com` | Route traffic to ALB |
| CNAME | `_3a1684def09da29d98087d0260dd3f9a.lchai` | `_d700c1768387dc6258c6d06c17ea933b.jkddzztszm.acm-validations.aws.` | ACM certificate validation |

---

*LCHAI v2.0 — AWS EKS Deployment — March 2026*
