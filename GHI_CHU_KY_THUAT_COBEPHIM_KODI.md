# GHI CHÚ KỸ THUẬT — CÔ BÉ PHIM KODI

Ngày tạo: 25/10/2026  
Addon: `plugin.video.cobephim`  
Repository: `repository.cobephim`

## Kiến trúc

- Giao diện Kodi native, không WebView.
- API danh sách/chi tiết/tập lấy từ `api_base`.
- Trang Phim bộ/Phim lẻ đọc dữ liệu Next.js server-rendered để không cần token đăng nhập.
- Trang xem server-rendered cung cấp object `episode` gồm `type` và `link`.
- Resolver mở trang embed, ưu tiên `signedMasterUrl`, sau đó `window.videoSrc`, source `.m3u8/.mp4`, cuối cùng ghép `baseUrl + videoHash + /master.m3u8`.
- Link phát gắn `User-Agent`, `Referer`, `Origin` để Kodi mở HLS đúng như trình phát web.

## Cấu hình động

Plugin đọc file:

`https://raw.githubusercontent.com/TNB88/cobephim.kodi/main/config.json`

Các trường có thể đổi mà không cần build lại plugin:

- `site_base`: domain trang web.
- `api_base`: API JSON.
- `embed_base`: host embed nội bộ.
- `image_base`: host hình ảnh.

Plugin kiểm tra mọi giá trị phải là HTTPS hợp lệ và cache cấu hình tốt gần nhất trong profile addon. Nếu GitHub lỗi, dùng cache; nếu chưa có cache, dùng cấu hình mặc định đóng trong plugin.

## Quy trình cập nhật plugin

1. Sửa source và tăng version trong `plugin.video.cobephim/addon.xml`.
2. Compile Python và chạy smoke test API/list/detail/episode/resolver.
3. Tạo ZIP có đúng thư mục gốc `plugin.video.cobephim/`.
4. Chép ZIP vào thư mục `plugin.video.cobephim/` của repository GitHub.
5. Cập nhật `addons.xml`, tính lại `addons.xml.md5`, commit và push.

Người dùng chỉ cần cài `repository.cobephim-1.0.0.zip` một lần và bật tự động cập nhật trong Kodi.
