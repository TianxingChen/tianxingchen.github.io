const shareButton = document.getElementById('share-button');
const shareStatus = document.getElementById('share-status');
const english = document.documentElement.lang === 'en';

if (navigator.clipboard && window.isSecureContext) {
  shareButton.hidden = false;
  shareButton.addEventListener('click', async () => {
    try {
      const url = document.querySelector('link[rel="canonical"]').href;
      await navigator.clipboard.writeText(url);
      shareStatus.textContent = english ? 'Article link copied' : '文章链接已复制';
    } catch {
      shareStatus.textContent = english ? 'Please copy the link from the address bar' : '请从地址栏复制链接';
    }
  });
}
