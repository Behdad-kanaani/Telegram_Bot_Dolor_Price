export default {
    async fetch(request) {
        try {
            const url = new URL(request.url);

            // 🔐 توکن امنیتی ثابت داخل کد
            const SECRET_TOKEN = "myStrongSecret123";

            // بررسی توکن از هدر
            const token = request.headers.get("x-access-token");
            if (token !== SECRET_TOKEN) {
                return new Response("Unauthorized: Invalid or missing token", { status: 401 });
            }

            // گرفتن مقصد از query string
            const target = url.searchParams.get("target");
            if (!target) {
                return new Response("Error: target parameter is required, e.g. ?target=https://example.com", {
                    status: 400,
                });
            }

            // بررسی فرمت URL
            if (!/^https?:\/\//i.test(target)) {
                return new Response("Error: target must start with http:// or https://", { status: 400 });
            }

            const targetUrl = new URL(target);

            // **تغییر:** اضافه کردن api.telegram.org به لیست دامنه‌های مجاز
            const allowedHosts = ["httpbin.org", "api.github.com", "example.com", "api.telegram.org"]; 
            if (!allowedHosts.includes(targetUrl.hostname)) {
                return new Response(`Access to ${targetUrl.hostname} is not allowed`, { status: 403 });
            }

            // محدودیت سایز بدنه (10MB)
            const contentLength = request.headers.get("content-length");
            if (contentLength && parseInt(contentLength) > 10_000_000) {
                return new Response("Request body too large", { status: 413 });
            }

            // ساخت درخواست جدید
            const proxyRequest = new Request(targetUrl, {
                method: request.method,
                headers: request.headers,
                body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
            });

            proxyRequest.headers.set("X-Proxy-By", "Cloudflare-Worker");

            // ارسال با timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 ثانیه
            const response = await fetch(proxyRequest, { signal: controller.signal });
            clearTimeout(timeoutId);

            // برگرداندن پاسخ
            return new Response(response.body, {
                status: response.status,
                headers: response.headers,
            });

        } catch (err) {
            if (err.name === "AbortError") {
                return new Response("Request timed out", { status: 504 });
            }
            return new Response(`Tunnel Error: ${err.message}`, { status: 502 });
        }
    },
};
