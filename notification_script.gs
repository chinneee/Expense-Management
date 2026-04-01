/**
 * CHI TIÊU CÁ NHÂN — GOOGLE APPS SCRIPT
 * Gửi email nhắc nhở lúc 9PM nếu hôm đó chưa nhập khoản chi.
 *
 * HƯỚNG DẪN SETUP:
 * 1. Mở Google Sheet → Extensions → Apps Script
 * 2. Paste toàn bộ code này vào
 * 3. Chỉnh EMAIL và SHEET_NAME bên dưới
 * 4. Chạy setupTrigger() một lần duy nhất để tạo trigger tự động
 */

// ── CONFIG ─────────────────────────────────────────────────────────────────
const YOUR_EMAIL   = "your@email.com";      // ← Đổi thành email của bạn
const SHEET_NAME   = "ChiTieuCaNhan";       // ← Tên Google Sheet
const WORKSHEET    = "Data";
const BENCHMARK    = 200000;               // VNĐ
// ───────────────────────────────────────────────────────────────────────────

function checkAndNotify() {
  const ss       = SpreadsheetApp.openByUrl(getSheetUrl());
  const sheet    = ss.getSheetByName(WORKSHEET);
  const data     = sheet.getDataRange().getValues();

  if (data.length <= 1) {
    // Không có dữ liệu nào (chỉ có header)
    sendReminder(0);
    return;
  }

  const today = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  let totalToday = 0;
  let hasEntry   = false;

  for (let i = 1; i < data.length; i++) {
    const rowDate = Utilities.formatDate(new Date(data[i][0]), "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
    if (rowDate === today) {
      hasEntry    = true;
      totalToday += Number(data[i][2]) || 0;
    }
  }

  if (!hasEntry) {
    sendReminder(0);
  } else if (totalToday > BENCHMARK) {
    sendOverBudgetAlert(totalToday);
  }
  // Nếu trong budget → không gửi mail (không làm phiền)
}


function sendReminder(total) {
  const today = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy");

  const subject = `⏰ Nhắc nhở: Bạn chưa cập nhật chi tiêu hôm nay (${today})`;
  const body = `
Xin chào,

Hôm nay (${today}) bạn chưa ghi nhận khoản chi tiêu nào.

👉 Mở app để cập nhật: [LINK_APP_CỦA_BẠN]

Đừng để dữ liệu bị hụt nhé! Chỉ mất 30 giây thôi.

—
Chi Tiêu Cá Nhân App
  `.trim();

  MailApp.sendEmail({
    to:      YOUR_EMAIL,
    subject: subject,
    body:    body,
  });

  Logger.log("Đã gửi email nhắc nhở.");
}


function sendOverBudgetAlert(total) {
  const today = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy");
  const over  = total - BENCHMARK;

  const subject = `⚠️ Vượt benchmark chi tiêu hôm nay (${today})`;
  const body = `
Xin chào,

Hôm nay (${today}) bạn đã chi tiêu:
  Tổng: ${total.toLocaleString("vi-VN")}đ
  Benchmark: ${BENCHMARK.toLocaleString("vi-VN")}đ
  Vượt quá: ${over.toLocaleString("vi-VN")}đ

💡 Hãy xem lại các khoản chi để điều chỉnh cho ngày mai nhé.

👉 Xem chi tiết: [LINK_APP_CỦA_BẠN]

—
Chi Tiêu Cá Nhân App
  `.trim();

  MailApp.sendEmail({
    to:      YOUR_EMAIL,
    subject: subject,
    body:    body,
  });

  Logger.log(`Đã gửi email cảnh báo vượt budget: ${total}`);
}


/**
 * Chạy hàm này 1 lần để cài đặt trigger tự động lúc 9PM mỗi ngày.
 * Vào Apps Script → Run → setupTrigger
 */
function setupTrigger() {
  // Xoá trigger cũ nếu có
  const triggers = ScriptApp.getProjectTriggers();
  for (const t of triggers) {
    if (t.getHandlerFunction() === "checkAndNotify") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // Tạo trigger mới: 9PM (21:00) giờ VN mỗi ngày
  ScriptApp.newTrigger("checkAndNotify")
    .timeBased()
    .atHour(21)
    .nearMinute(0)
    .everyDays(1)
    .inTimezone("Asia/Ho_Chi_Minh")
    .create();

  Logger.log("✅ Trigger đã được cài đặt: 9PM mỗi ngày.");
}


/**
 * Helper: lấy URL Google Sheet hiện tại.
 * Nếu chạy từ script gắn với sheet thì dùng cách này.
 */
function getSheetUrl() {
  return SpreadsheetApp.getActiveSpreadsheet().getUrl();
}
