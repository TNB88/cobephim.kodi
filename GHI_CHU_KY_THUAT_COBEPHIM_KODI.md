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

## Bản phát hành 1.0.0

- Repository GitHub: `https://github.com/TNB88/cobephim.kodi`.
- Gói cài kho: `C:\cobephim kodi\repository.cobephim\repository.cobephim-1.0.0.zip`; kích thước `938` byte; SHA-256 `B420DF1853F38BB761D3FB0D0F26FE4D77BAAAF3B90C4C133AC15C224A34B832`.
- Gói cài trực tiếp plugin: `C:\cobephim kodi\plugin.video.cobephim\plugin.video.cobephim-1.0.0.zip`; kích thước `9,199` byte; SHA-256 `AAEC5E94CAB061E8ED58728247658723A002C37CEF47C04BBAD54DAEF3915F7F`.
- ZIP plugin có đúng thư mục gốc `plugin.video.cobephim/`, không chứa `__pycache__`, `.pyc` hoặc ZIP cũ.
- `addons.xml.md5` đã đối chiếu đúng MD5 của file `addons.xml` tải lại từ GitHub.

## Kiểm thử 25/10/2026

- Python compile: đạt.
- XML/JSON cấu hình và repository: đạt.
- Phim hot: `6` mục.
- Phim bộ trang 1: `32` mục, tổng `436` trang.
- Phim lẻ trang 1: `32` mục, tổng `609` trang.
- Bộ sưu tập trang chủ: `4` nhóm; nhóm đầu có `20` phim.
- Tìm kiếm `superman`: `30` kết quả.
- Chi tiết, server và danh sách tập: đạt.
- Resolver tách được HLS thật từ `streamvsmov`; tải playlist trả HTTP 200 và bắt đầu bằng `#EXTM3U`.
- Tải lại `config.json`, hai ZIP, `addons.xml` và checksum từ GitHub raw: đạt.
