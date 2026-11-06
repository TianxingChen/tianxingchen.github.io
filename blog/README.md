# Blog statistics

`assets/stats.js` uses the public [self-hosted Busuanzi service](https://busuanzi.9420.ltd/) and its [API](https://github.com/soxft/busuanzi/wiki/API). The endpoint is the one currently returned by its official `/js` client. No account, API key, third-party JavaScript, cookies, or local storage are needed by this integration. Requests send the canonical article URL to the counter service, which also receives ordinary HTTP connection information.

- A live article load records one page view (PV), including refreshes. This is not a unique visitor count or proof that the article was read.
- Chinese and English pages use the same article key, e.g. `eai-definition-first`.
- The homepage and blog lists only read counts. Their total is the sum of the article counts shown in the list, excluding list/homepage visits.
- Only `https://tianxingchen.github.io` can record from this script; local previews only read live counts.
- Counts begin when tracking is enabled; earlier traffic cannot be recovered. The public service does not guarantee uptime or data retention. An unavailable count displays `—`, never a fabricated zero or partial total.

For a new article, set `data-blog-article="slug"` on its body and `data-blog-views="slug"` on count labels in its article and listing pages. Include `assets/stats.js` using the appropriate relative path. Both language versions should use the same slug. Update the article count in the blog headers when adding posts.

Reading-time labels are static and work without JavaScript. The estimate uses the article body (including captions), at 400 CJK characters/minute plus 220 other words/minute, rounded up to at least one minute. To refresh labels after editing prose:

```sh
python3 scripts/update_blog_reading_time.py
node --test scripts/test_blog_stats.cjs
```

Use `<span data-reading-time="slug" data-reading-language="zh">…</span>` (or `en`) for each reading-time label. The script updates the homepage, blog lists, and articles together.
