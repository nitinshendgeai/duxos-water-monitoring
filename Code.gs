/**
 * Water Monitoring System — Backend (Google Apps Script)
 * ---------------------------------------------------------
 * Receives form submissions from the web app and appends a row
 * to the correct sheet: Meter_Readings or Tank_Status.
 *
 * Deployed as a Web App (Deploy > New deployment > Web app,
 * execute as yourself, access: Anyone). Paste this whole file into
 * the Apps Script editor bound to the target Google Sheet.
 *
 * This file also includes the ATTENDANCE SYSTEM add-on (search for
 * "ATTENDANCE SYSTEM" below). It shares this same doGet/doPost and
 * deployment, but reads/writes its own separate tabs (Att_Staff,
 * Att_Attendance, Att_Config) and never touches Meter_Readings or
 * Tank_Status.
 *
 * VERSION MARKER: "merged-v3-validated" — added to the plain
 * health-check response below so you can confirm, just by opening
 * the bare /exec URL with no params, whether THIS exact code is what
 * a given deployment is actually running.
 */

// Sheet name constants — must match your actual tab names exactly.
const SHEET_METER = 'Meter_Readings';
const SHEET_TANK = 'Tank_Status';

/**
 * Entry point for all POST requests from the web app.
 * Expects JSON body: { formType: 'meter' | 'tank', data: {...} }
 */
function doPost(e) {
  // --- ATTENDANCE SYSTEM: give it first look; it returns null if the
  // request isn't one of its own (e.g. no "action" starting with "att_"),
  // in which case everything below runs exactly as it always has. ---
  const attResult = attDoPost(e);
  if (attResult) return attResult;

  try {
    const payload = JSON.parse(e.postData.contents);
    const formType = payload.formType;
    const data = payload.data;

    if (formType === 'meter') {
      validateMeterData(data);
      appendMeterReading(data);
    } else if (formType === 'tank') {
      validateTankData(data);
      appendTankStatus(data);
    } else {
      return jsonResponse({ status: 'error', message: 'Unknown formType: ' + formType });
    }

    return jsonResponse({ status: 'success' });

  } catch (err) {
    return jsonResponse({ status: 'error', message: err.message });
  }
}

/**
 * Basic server-side guardrails for Meter Reading submissions. Mirrors
 * the "required"/numeric constraints already on the form, since the
 * client-side ones are trivially bypassable by anyone calling the
 * Web App URL directly. Throws with a clear message on failure,
 * which doPost() turns into a normal { status: 'error' } response.
 */
function validateMeterData(data) {
  if (!data) throw new Error('Missing form data.');
  if (!data.date) throw new Error('Date is required.');
  if (!data.recordedBy) throw new Error('Recorded By is required.');
  ['wingA', 'wingB', 'wingC'].forEach(function (field) {
    const n = Number(data[field]);
    if (data[field] === '' || data[field] === undefined || isNaN(n)) {
      throw new Error('Meter reading for ' + field + ' must be a number.');
    }
    if (n < 0) throw new Error('Meter reading for ' + field + ' cannot be negative.');
  });
}

/**
 * Basic server-side guardrails for Tank Status submissions. Litre
 * fields must be non-negative numbers; percentage fields must be
 * numbers within 0-100.
 */
function validateTankData(data) {
  if (!data) throw new Error('Missing form data.');
  if (!data.date) throw new Error('Date is required.');
  if (!data.session) throw new Error('Session is required.');

  const litreFields = ['ugDomesticAB', 'ugDomesticC', 'ugFlushingAB', 'ugFlushingC'];
  litreFields.forEach(function (field) {
    const n = Number(data[field]);
    if (data[field] === '' || data[field] === undefined || isNaN(n)) {
      throw new Error(field + ' must be a number.');
    }
    if (n < 0) throw new Error(field + ' cannot be negative.');
  });

  const percentFields = ['fireTank', 'ohDomA', 'ohDomB', 'ohDomC', 'ohFlushA', 'ohFlushB', 'ohFlushC'];
  percentFields.forEach(function (field) {
    const n = Number(data[field]);
    if (data[field] === '' || data[field] === undefined || isNaN(n)) {
      throw new Error(field + ' must be a number.');
    }
    if (n < 0 || n > 100) throw new Error(field + ' must be between 0 and 100.');
  });
}

/**
 * Appends one row to Meter_Readings.
 * Column order must match the sheet exactly:
 * Date | Time | Recorded By | Wing A | Wing B | Wing C | Remarks | Created Timestamp
 */
function appendMeterReading(data) {
  const sheet = getSheet(SHEET_METER);
  sheet.appendRow([
    data.date,
    data.time,
    data.recordedBy,
    data.wingA,
    data.wingB,
    data.wingC,
    data.remarks || '',
    new Date()
  ]);
}

/**
 * Appends one row to Tank_Status.
 * Column order must match the sheet exactly:
 * Date | Time | Session | UG Domestic A+B | UG Domestic C | UG Flushing A+B | UG Flushing C |
 * Fire Tank Level | OH Domestic A | OH Domestic B | OH Domestic C |
 * OH Flushing A | OH Flushing B | OH Flushing C | Remarks | Created Timestamp
 */
function appendTankStatus(data) {
  const sheet = getSheet(SHEET_TANK);
  sheet.appendRow([
    data.date,
    data.time,
    data.session,
    data.ugDomesticAB,
    data.ugDomesticC,
    data.ugFlushingAB,
    data.ugFlushingC,
    data.fireTank,
    data.ohDomA,
    data.ohDomB,
    data.ohDomC,
    data.ohFlushA,
    data.ohFlushB,
    data.ohFlushC,
    data.remarks || '',
    new Date()
  ]);
}

/**
 * Gets a sheet by name, throws a clear error if it doesn't exist.
 */
function getSheet(name) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sheet) {
    throw new Error('Sheet not found: ' + name);
  }
  return sheet;
}

/**
 * IMPORTANT: Google Sheets auto-detects text that looks like a date
 * (e.g. "29 Jul 2026") and silently converts it into a real Date value
 * in any column formatted as Date/Time. When read back with
 * getValues(), that cell comes back as a JS Date object instead of the
 * original text — and if sent to the browser as-is, it gets serialized
 * to a UTC ISO timestamp, which can show the wrong date/time depending
 * on timezone (this was the "Last Updated shows wrong" bug).
 *
 * This helper normalizes any such value back into a clean, correctly
 * formatted string in the script's own timezone, while leaving plain
 * text values untouched. Use it for every Date/Time column read.
 */
function formatCellValue(value, format) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), format);
  }
  return value;
}

/**
 * Wraps a JS object as a JSON text response.
 */
function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Handles GET requests.
 * - No params: health check (confirms the script is deployed and reachable).
 * - ?action=latest: returns the latest Tank_Status row, last 7 Meter_Readings
 *   entries, and today's activity status — everything the Dashboard needs.
 */
function doGet(e) {
  // --- ATTENDANCE SYSTEM: give it first look; it returns null if the
  // request isn't one of its own (action=att_data), in which case
  // everything below runs exactly as it always has. ---
  const attResult = attDoGet(e);
  if (attResult) return attResult;

  const action = e && e.parameter ? e.parameter.action : null;

  if (action === 'latest') {
    try {
      return jsonResponse({
        status: 'success',
        latestTank: getLatestTankStatus(),
        recentMeterReadings: getRecentMeterReadings(7),
        todayActivities: getTodayActivities()
      });
    } catch (err) {
      return jsonResponse({ status: 'error', message: err.message });
    }
  }

  return jsonResponse({
    status: 'ok',
    message: 'Water Monitoring backend is running.',
    version: 'merged-v3-validated'
  });
}

/**
 * Returns the most recently added row from Tank_Status as an object,
 * or null if the sheet has no data rows yet.
 * Column order must match appendTankStatus() above.
 */
function getLatestTankStatus() {
  const sheet = getSheet(SHEET_TANK);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return null; // only header row, or empty

  const row = sheet.getRange(lastRow, 1, 1, 16).getValues()[0];

  return {
    date: formatCellValue(row[0], 'd MMM yyyy'),
    time: formatCellValue(row[1], 'h:mm a'),
    session: row[2],
    ugDomesticAB: row[3],
    ugDomesticC: row[4],
    ugFlushingAB: row[5],
    ugFlushingC: row[6],
    fireTank: row[7],
    ohDomA: row[8],
    ohDomB: row[9],
    ohDomC: row[10],
    ohFlushA: row[11],
    ohFlushB: row[12],
    ohFlushC: row[13],
    remarks: row[14]
  };
}

/**
 * Returns the last N rows from Meter_Readings, most recent first.
 * Column order must match appendMeterReading() above.
 */
function getRecentMeterReadings(count) {
  const sheet = getSheet(SHEET_METER);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return []; // only header row, or empty

  const numRows = Math.min(count, lastRow - 1);
  const startRow = lastRow - numRows + 1;
  const rows = sheet.getRange(startRow, 1, numRows, 8).getValues();

  return rows.reverse().map(function (row) {
    return {
      date: formatCellValue(row[0], 'd MMM yyyy'),
      time: formatCellValue(row[1], 'h:mm a'),
      recordedBy: row[2],
      wingA: row[3],
      wingB: row[4],
      wingC: row[5],
      remarks: row[6]
    };
  });
}

/**
 * Checks real entries against today's date to determine which of the
 * day's activities have actually happened, based on the "Created
 * Timestamp" column (set by the server when each row was saved) —
 * not the Date field typed by staff, since that's just display text.
 */
function getTodayActivities() {
  const now = new Date();
  return {
    meterReadingDone: hasRowToday(SHEET_METER, 8, now),
    morningTankDone: hasTankSessionToday('Morning', now),
    afternoonTankDone: hasTankSessionToday('Afternoon', now),
    nightTankDone: hasTankSessionToday('Night', now)
  };
}

/**
 * Returns true if any row in the given sheet has a Created Timestamp
 * (in timestampCol, 1-indexed) matching today's date.
 */
function hasRowToday(sheetName, timestampCol, now) {
  const sheet = getSheet(sheetName);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;

  const numRows = lastRow - 1;
  const timestamps = sheet.getRange(2, timestampCol, numRows, 1).getValues();

  for (let i = 0; i < timestamps.length; i++) {
    const ts = timestamps[i][0];
    if (ts instanceof Date && isSameLocalDay(ts, now)) return true;
  }
  return false;
}

/**
 * Returns true if Tank_Status has a row for the given session
 * ("Morning" / "Afternoon" / "Night") with a Created Timestamp
 * matching today's date.
 */
function hasTankSessionToday(sessionName, now) {
  const sheet = getSheet(SHEET_TANK);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;

  const numRows = lastRow - 1;
  // Session is column 3, Created Timestamp is column 16.
  const data = sheet.getRange(2, 3, numRows, 14).getValues(); // cols 3..16

  for (let i = 0; i < data.length; i++) {
    const session = data[i][0];       // column 3
    const timestamp = data[i][13];    // column 16 (14th column in this range)
    if (session === sessionName && timestamp instanceof Date && isSameLocalDay(timestamp, now)) {
      return true;
    }
  }
  return false;
}

/** Compares two Date objects by calendar day, ignoring time. */
function isSameLocalDay(d1, d2) {
  return d1.getFullYear() === d2.getFullYear() &&
         d1.getMonth() === d2.getMonth() &&
         d1.getDate() === d2.getDate();
}


/* ============================================================================
 * ATTENDANCE SYSTEM — add-on (3-Wing Security & Staff attendance)
 * ============================================================================
 * Everything below is new. It shares the doGet/doPost above (see the two
 * "ATTENDANCE SYSTEM" hooks added near the top of each) but is otherwise
 * fully self-contained:
 *   - Its own tabs: Att_Staff, Att_Attendance, Att_Config (auto-created on
 *     first use — it never reads or writes Meter_Readings or Tank_Status).
 *   - Its own request tag: every action it recognises starts with "att_",
 *     so it never collides with formType/action values used above.
 *   - Its own helper functions, all prefixed "att" so none of them can
 *     shadow or clash with the Water Monitoring helpers above
 *     (getSheet, jsonResponse, etc. above are untouched).
 *
 * Data model:
 *   Att_Staff:      ID | Name | Role | Phone | Code
 *   Att_Attendance: Timestamp | Date | StaffID | Type | Location
 *   Att_Config:     Key | Value   (stores wing/location names + admin PIN)
 *
 * Roles: security (Wing A/B/C), technical (Office), manager (Office & Gym),
 * gym_attendant (Gym).
 *
 * ADMIN AUTH: every mutating admin action (add/delete staff, save config,
 * clear all) requires a "pin" field in the request body, checked against
 * Att_Config server-side. The raw PIN is never sent back to the client —
 * att_verifyPin only returns ok/fail. This closes a real security gap:
 * previously att_data (a public, unauthenticated GET used just to render
 * the check-in screen) returned the actual admin PIN in plain text, and
 * none of the mutating endpoints checked a PIN at all — anyone with the
 * deployed URL could wipe all attendance data with a single POST.
 * ========================================================================= */

const ATT_STAFF_SHEET = 'Att_Staff';
const ATT_LOG_SHEET = 'Att_Attendance';
const ATT_CONFIG_SHEET = 'Att_Config';

const ATT_STAFF_HEADERS = ['ID', 'Name', 'Role', 'Phone', 'Code'];
const ATT_LOG_HEADERS = ['Timestamp', 'Date', 'StaffID', 'Type', 'Location', 'Shift'];
const ATT_CONFIG_HEADERS = ['Key', 'Value'];

/** Gets (or creates, with headers) one of the attendance tabs. */
function attGetSheet_(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
  }
  return sheet;
}

/** Reads all data rows of a sheet into an array of {Header: value} objects. */
function attReadRows_(sheet) {
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) return [];
  const headers = values[0];
  return values.slice(1)
    .filter(row => row.some(c => c !== ''))
    .map(row => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = row[i]; });
      return obj;
    });
}

/** Wraps a JS object as a JSON text response (attendance-only helper). */
function attJsonOut_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Today's date as yyyy-MM-dd in the script's timezone. */
function attTodayKey_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/**
 * Google Sheets sometimes auto-converts a "Date" column's text
 * (e.g. "2026-08-05") into a real Date value once it looks like a
 * date. When read back via getValues(), that comes back as a JS
 * Date object instead of the original string, which silently breaks
 * every `r.Date === dateKey` string comparison below (the exact same
 * class of bug the Water Monitoring code above already works around
 * with formatCellValue). This normalizes either shape back into a
 * plain 'yyyy-MM-dd' string so comparisons always work.
 */
function attNormalizeDate_(value) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  return value;
}

/**
 * Default shift when the client doesn't send one: 8am-8pm (script's
 * timezone) counts as Day, 8pm-8am counts as Night. The client
 * normally sends its own choice explicitly (see att_checkin below),
 * this is just a safety fallback.
 */
function attDefaultShift_() {
  const hour = Number(Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'H'));
  return (hour >= 8 && hour < 20) ? 'day' : 'night';
}

/** Reads wing/location names + admin PIN from Att_Config, with sane defaults. */
function attGetConfig_() {
  const sheet = attGetSheet_(ATT_CONFIG_SHEET, ATT_CONFIG_HEADERS);
  const rows = attReadRows_(sheet);
  const config = {};
  rows.forEach(r => { config[r.Key] = r.Value; });

  let wings;
  try { wings = config.wings ? JSON.parse(config.wings) : null; } catch (e) { wings = null; }
  if (!wings) {
    wings = { A: { name: 'Wing A' }, B: { name: 'Wing B' }, C: { name: 'Wing C' }, OFFICE: { name: 'Office' }, GYM: { name: 'Gym' } };
  }
  return { pin: config.pin || '1234', wings };
}

/** Upserts one key/value row in Att_Config. */
function attSetConfigValue_(key, value) {
  const sheet = attGetSheet_(ATT_CONFIG_SHEET, ATT_CONFIG_HEADERS);
  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === key) {
      sheet.getRange(i + 1, 2).setValue(value);
      return;
    }
  }
  sheet.appendRow([key, value]);
}

/** True if the given pin matches the currently configured admin PIN. */
function attCheckPin_(pin) {
  const config = attGetConfig_();
  return !!pin && String(pin) === String(config.pin);
}

/**
 * Attendance GET handler — called from the shared doGet(e) above.
 * Returns null (meaning "not mine, keep going") for any request that
 * isn't ?action=att_data, so the Water Monitoring GET logic runs untouched.
 */
function attDoGet(e) {
  const action = e.parameter && e.parameter.action;
  if (action !== 'att_data') return null;

  const dateKey = e.parameter.date || attTodayKey_();

  const staffSheet = attGetSheet_(ATT_STAFF_SHEET, ATT_STAFF_HEADERS);
  const staff = attReadRows_(staffSheet).map(r => ({
    id: String(r.ID), name: r.Name, role: r.Role, phone: String(r.Phone), code: String(r.Code)
  }));

  const logSheet = attGetSheet_(ATT_LOG_SHEET, ATT_LOG_HEADERS);
  const attendance = attReadRows_(logSheet)
    .filter(r => attNormalizeDate_(r.Date) === dateKey)
    .map(r => ({ staffId: String(r.StaffID), type: r.Type, wing: r.Location, time: r.Timestamp, shift: r.Shift || '' }));

  const config = attGetConfig_();
  // NOTE: the admin PIN itself is deliberately NOT included here — this
  // endpoint is public and unauthenticated. Admin unlock is verified via
  // att_verifyPin instead, so the real PIN never reaches the client.
  return attJsonOut_({ ok: true, staff, attendance, wings: config.wings });
}

/**
 * Attendance POST handler — called from the shared doPost(e) above.
 * Returns null for any request whose body.action doesn't start with
 * "att_", so the Water Monitoring POST logic runs untouched.
 */
function attDoPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return null; }

  const action = body.action;
  if (!action || action.indexOf('att_') !== 0) return null;

  // --- Verify an entered admin PIN without ever exposing the real one ---
  if (action === 'att_verifyPin') {
    return attJsonOut_({ ok: attCheckPin_(body.pin) });
  }

  // --- Add a new staff member; auto-generates a unique 4-digit login code ---
  if (action === 'att_addStaff') {
    if (!attCheckPin_(body.pin)) return attJsonOut_({ ok: false, error: 'Incorrect admin PIN.' });
    if (!body.name) return attJsonOut_({ ok: false, error: 'Name is required.' });
    const sheet = attGetSheet_(ATT_STAFF_SHEET, ATT_STAFF_HEADERS);
    const existingCodes = attReadRows_(sheet).map(r => String(r.Code));
    let code;
    do { code = String(Math.floor(1000 + Math.random() * 9000)); } while (existingCodes.indexOf(code) !== -1);
    const id = 's_' + Date.now() + '_' + Math.floor(Math.random() * 10000);
    sheet.appendRow([id, body.name, body.role, body.phone || '', code]);
    return attJsonOut_({ ok: true, staff: { id: id, name: body.name, role: body.role, phone: body.phone || '', code: code } });
  }

  // --- Remove a staff member (their past attendance rows are kept) ---
  if (action === 'att_deleteStaff') {
    if (!attCheckPin_(body.pin)) return attJsonOut_({ ok: false, error: 'Incorrect admin PIN.' });
    const sheet = attGetSheet_(ATT_STAFF_SHEET, ATT_STAFF_HEADERS);
    const values = sheet.getDataRange().getValues();
    for (let i = 1; i < values.length; i++) {
      if (String(values[i][0]) === String(body.id)) {
        sheet.deleteRow(i + 1);
        break;
      }
    }
    return attJsonOut_({ ok: true });
  }

  // --- QR check-in/out: looks up the code, toggles in/out based on today's last event ---
  // Intentionally not PIN-gated — this is the public check-in flow, guarded
  // by each staff member's own personal code instead.
  if (action === 'att_checkin') {
    const staffSheet = attGetSheet_(ATT_STAFF_SHEET, ATT_STAFF_HEADERS);
    const staffRows = attReadRows_(staffSheet);
    const match = staffRows.find(r => String(r.Code) === String(body.code));
    if (!match) return attJsonOut_({ ok: false, error: 'Code not recognised' });

    const dateKey = body.date || attTodayKey_();
    const logSheet = attGetSheet_(ATT_LOG_SHEET, ATT_LOG_HEADERS);
    const todaysRows = attReadRows_(logSheet).filter(r => attNormalizeDate_(r.Date) === dateKey && String(r.StaffID) === String(match.ID));

    let lastType = null;
    if (todaysRows.length) {
      todaysRows.sort((a, b) => new Date(a.Timestamp) - new Date(b.Timestamp));
      lastType = todaysRows[todaysRows.length - 1].Type;
    }
    const nextType = lastType === 'in' ? 'out' : 'in';
    const shift = body.shift || attDefaultShift_();
    const iso = new Date().toISOString();
    logSheet.appendRow([iso, dateKey, String(match.ID), nextType, body.location, shift]);

    return attJsonOut_({
      ok: true, type: nextType, time: iso, shift: shift,
      staff: { id: String(match.ID), name: match.Name, role: match.Role, phone: String(match.Phone) }
    });
  }

  // --- Save wing/location names and/or the admin PIN into Att_Config ---
  if (action === 'att_saveConfig') {
    if (!attCheckPin_(body.pin)) return attJsonOut_({ ok: false, error: 'Incorrect admin PIN.' });
    if (body.wings) attSetConfigValue_('wings', JSON.stringify(body.wings));
    if (body.newPin) attSetConfigValue_('pin', body.newPin);
    return attJsonOut_({ ok: true });
  }

  // --- Wipe all staff + attendance rows (keeps header rows) ---
  if (action === 'att_clearAll') {
    if (!attCheckPin_(body.pin)) return attJsonOut_({ ok: false, error: 'Incorrect admin PIN.' });
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    [ATT_STAFF_SHEET, ATT_LOG_SHEET].forEach(name => {
      const sheet = ss.getSheetByName(name);
      if (sheet && sheet.getLastRow() > 1) sheet.deleteRows(2, sheet.getLastRow() - 1);
    });
    return attJsonOut_({ ok: true });
  }

  return attJsonOut_({ ok: false, error: 'Unknown attendance action' });
}
