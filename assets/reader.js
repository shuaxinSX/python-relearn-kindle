/* reader.js: ES5, no frameworks */
"use strict";


function prlByteLength(s) {
  try { return unescape(encodeURIComponent(s)).length; }
  catch (e) { return s.length; }
}

function prlHasUnsafeKeys(v) {
  var k;
  if (v !== null && typeof v === "object") {
    for (k in v) {
      if (k === "__proto__" || k === "constructor" || k === "prototype") { return true; }
      if (prlHasUnsafeKeys(v[k])) { return true; }
    }
  }
  return false;
}

function prlIsNonNegInt(n) {
  return typeof n === "number" && isFinite(n) && Math.floor(n) === n && n >= 0;
}

function prlInArray(arr, v) {
  var i;
  for (i = 0; i < arr.length; i++) { if (arr[i] === v) { return true; } }
  return false;
}

function prlValidFields(s) {
  var k, v, loc;
  if (!s || typeof s !== "object") { return false; }
  if (!s.settings || typeof s.settings !== "object") { return false; }
  if (!(s.settings.fontSize === 22 || s.settings.fontSize === 26 || s.settings.fontSize === 30)) { return false; }
  loc = s.lastLocation;
  if (loc !== null) {
    if (!loc || typeof loc !== "object") { return false; }
    if (typeof loc.lessonId !== "string" || !loc.lessonId) { return false; }
    if (typeof loc.stepId !== "string" || !loc.stepId) { return false; }
  }
  if (!s.lessons || typeof s.lessons !== "object") { return false; }
  for (k in s.lessons) {
    v = s.lessons[k];
    if (!v || typeof v !== "object") { return false; }
    if (v.lastStepId !== undefined && typeof v.lastStepId !== "string") { return false; }
    if (v.completed !== undefined && typeof v.completed !== "boolean") { return false; }
    if (v.practiceDone !== undefined && typeof v.practiceDone !== "boolean") { return false; }
  }
  if (!s.questions || typeof s.questions !== "object") { return false; }
  for (k in s.questions) {
    v = s.questions[k];
    if (!v || typeof v !== "object") { return false; }
    if (!prlIsNonNegInt(v.revision) || v.revision <= 0) { return false; }
    if (!prlIsNonNegInt(v.attempts)) { return false; }
    if (!prlIsNonNegInt(v.wrongAttempts)) { return false; }
    if (v.lastOptionId !== null && v.lastOptionId !== undefined && typeof v.lastOptionId !== "string") { return false; }
    if (typeof v.lastCorrect !== "boolean") { return false; }
    if (typeof v.needsReview !== "boolean") { return false; }
    if (typeof v.lessonId !== "string" || !v.lessonId) { return false; }
    if (typeof v.stepId !== "string" || !v.stepId) { return false; }
  }
  return true;
}

/* opts: {courseId, maxBytes?, catalogLessons?, catalogQuestions?} */
function validateBackupText(text, opts) {
  opts = opts || {};
  var maxBytes = opts.maxBytes || 131072;
  var courseId = opts.courseId || "python-relearn";
  var catalogLessons = opts.catalogLessons || [];
  var catalogQuestions = opts.catalogQuestions || [];
  var s, k, v, read, review;
  if (typeof text !== "string") { return { ok: false, error: "invalid-json" }; }
  if (prlByteLength(text) > maxBytes) { return { ok: false, error: "too-large" }; }
  try { s = JSON.parse(text); }
  catch (e) { return { ok: false, error: "invalid-json" }; }
  if (prlHasUnsafeKeys(s)) { return { ok: false, error: "unsafe-keys" }; }
  if (!s || s.schemaVersion !== 1) { return { ok: false, error: "unknown-version" }; }
  if (s.courseId !== courseId) { return { ok: false, error: "course-mismatch" }; }
  if (!prlValidFields(s)) { return { ok: false, error: "bad-fields" }; }
  read = 0;
  review = 0;
  for (k in s.lessons) {
    v = s.lessons[k];
    if (v && v.completed === true && prlInArray(catalogLessons, k)) { read++; }
  }
  for (k in s.questions) {
    v = s.questions[k];
    if (v && v.needsReview === true && prlInArray(catalogQuestions, k)) { review++; }
  }
  return { ok: true, preview: { read: read, review: review }, state: s };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { validateBackupText: validateBackupText };
}


if (typeof document !== "undefined" && document.addEventListener) {
  document.addEventListener("DOMContentLoaded", function () { prlBoot(); });
}

function prlBoot() {
  var doc = document;
  var root = doc.documentElement;

  function addClass(el, c) {
    if (!el) { return; }
    if ((" " + el.className + " ").indexOf(" " + c + " ") < 0) {
      el.className = (el.className + " " + c).replace(/^\s+/, "");
    }
  }
  function removeClass(el, c) {
    if (!el) { return; }
    el.className = (" " + el.className + " ").replace(" " + c + " ", " ").replace(/^\s+|\s+$/g, "");
  }
  function closestTag(el, tag, cls) {
    while (el && el !== doc) {
      if (el.tagName && el.tagName.toLowerCase() === tag) {
        if (!cls || (" " + el.className + " ").indexOf(" " + cls + " ") >= 0) { return el; }
      }
      el = el.parentNode;
    }
    return null;
  }
  function clearChildren(el) {
    while (el && el.firstChild) { el.removeChild(el.firstChild); }
  }

  var cfg = (typeof window.PRL_CONFIG === "object" && window.PRL_CONFIG) || {};
  var siteId = cfg.siteId || "default";
  var basePath = cfg.basePath || "/";
  if (basePath.charAt(basePath.length - 1) !== "/") { basePath += "/"; }
  var courseId = cfg.courseId || "python-relearn";
  var STORE_KEY = "python-relearn:" + siteId + ":state";

  var storageOk = false;
  try {
    window.localStorage.setItem("__prl_probe__", "1");
    window.localStorage.removeItem("__prl_probe__");
    storageOk = true;
  } catch (e) { storageOk = false; }

  function defaultState() {
    return {
      schemaVersion: 1, courseId: courseId,
      settings: { fontSize: 26 }, lastLocation: null,
      lessons: {}, questions: {}
    };
  }

  function normalizeState(s) {
    var out = defaultState(), k, v;
    if (s.settings && (s.settings.fontSize === 22 || s.settings.fontSize === 26 || s.settings.fontSize === 30)) {
      out.settings.fontSize = s.settings.fontSize;
    }
    if (s.lastLocation) {
      out.lastLocation = { lessonId: s.lastLocation.lessonId, stepId: s.lastLocation.stepId };
    }
    for (k in s.lessons) {
      v = s.lessons[k];
      if (v && typeof v === "object") {
        out.lessons[k] = {
          lastStepId: (typeof v.lastStepId === "string" ? v.lastStepId : undefined),
          completed: v.completed === true,
          practiceDone: v.practiceDone === true
        };
      }
    }
    for (k in s.questions) {
      v = s.questions[k];
      if (v && typeof v === "object") {
        out.questions[k] = {
          revision: v.revision, attempts: v.attempts, wrongAttempts: v.wrongAttempts,
          lastOptionId: (typeof v.lastOptionId === "string" ? v.lastOptionId : null),
          lastCorrect: v.lastCorrect === true, needsReview: v.needsReview === true,
          lessonId: v.lessonId, stepId: v.stepId
        };
      }
    }
    return out;
  }

  var state = defaultState();
  var corruptMode = false;
  var corruptRaw = null;

  function loadState() {
    var raw = null, s = null;
    if (storageOk) {
      try { raw = window.localStorage.getItem(STORE_KEY); } catch (e) { raw = null; }
    }
    if (raw === null || raw === undefined) { return; }
    try {
      s = JSON.parse(raw);
      if (!s || s.schemaVersion !== 1) { throw new Error("version"); }
      if (!prlValidFields(s)) { throw new Error("fields"); }
    } catch (e) {
      corruptMode = true;
      corruptRaw = raw;
      state = defaultState();
      return;
    }
    state = normalizeState(s);
  }

  function persist(force) {
    if (corruptMode && !force) { return false; }
    if (!storageOk && !force) { return false; }
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(state));
      return true;
    } catch (e) { return false; }
  }

  function ensureLesson(lessonId) {
    if (!state.lessons[lessonId]) {
      state.lessons[lessonId] = { completed: false, practiceDone: false };
    }
    return state.lessons[lessonId];
  }

  /* keep font size, wipe project key only */
  function wipeKeepingFontSize() {
    var fs = state.settings.fontSize;
    try { window.localStorage.removeItem(STORE_KEY); } catch (e) {}
    corruptMode = false;
    state = defaultState();
    state.settings.fontSize = fs;
    persist(true);
    window.location.reload();
  }

  function showBanner() {
    var b = doc.getElementById("save-banner");
    if (b) {
      b.removeAttribute("hidden");
      b.textContent = "本地保存不可用；刷新或跨页面后，临时记录可能丢失";
    }
  }

  function countReview() {
    var k, n = 0;
    for (k in state.questions) {
      if (state.questions[k] && state.questions[k].needsReview === true) { n++; }
    }
    return n;
  }

  function applyFontSize(n) {
    var body = doc.body;
    removeClass(body, "fs-22"); removeClass(body, "fs-26"); removeClass(body, "fs-30");
    addClass(body, "fs-" + n);
  }
  function bindFontRadios() {
    var radios = doc.querySelectorAll('input[name="fs"]'), i;
    for (i = 0; i < radios.length; i++) {
      (function (r) {
        var v = parseInt(r.value, 10);
        if (v === state.settings.fontSize) { r.checked = true; }
        r.onchange = function () {
          var n = parseInt(r.value, 10);
          if (n === 22 || n === 26 || n === 30) {
            state.settings.fontSize = n;
            applyFontSize(n);
            persist();
          }
        };
      })(radios[i]);
    }
  }

  var bodyClass = " " + doc.body.className + " ";
  function hasPage(name) { return bodyClass.indexOf(" " + name + " ") >= 0; }
  function isReviewMode() { return (window.location.search || "").indexOf("review=1") >= 0; }

  function initSteps(article, lessonId, reviewMode) {
    var stepEls = article.querySelectorAll("section.step"), i;
    if (!stepEls || !stepEls.length) { return; }
    var ids = [];
    for (i = 0; i < stepEls.length; i++) { ids.push(stepEls[i].id); }
    var nav = doc.getElementById("step-nav");
    var end = article.querySelector(".lesson-end");
    var readMark = end ? end.querySelector(".read-mark") : null;
    var current = null;

    function renderNav(idx) {
      var prev, next, info;
      if (!nav) { return; }
      nav.removeAttribute("hidden");
      clearChildren(nav);
      prev = doc.createElement("button");
      prev.type = "button"; prev.textContent = "上一部分";
      next = doc.createElement("button");
      next.type = "button"; next.textContent = "下一部分";
      info = doc.createElement("span");
      info.className = "step-count";
      info.textContent = "第 " + (idx + 1) + " / " + ids.length + " 部分";
      if (idx <= 0) { prev.setAttribute("disabled", "disabled"); }
      else {
        (function (id) { prev.onclick = function () { window.location.hash = id; }; })(ids[idx - 1]);
      }
      if (idx >= ids.length - 1) { next.setAttribute("disabled", "disabled"); }
      else {
        (function (id) { next.onclick = function () { window.location.hash = id; }; })(ids[idx + 1]);
      }
      nav.appendChild(prev); nav.appendChild(info); nav.appendChild(next);
    }

    function show(id, save) {
      var idx = -1, j, h, top, n;
      for (j = 0; j < ids.length; j++) { if (ids[j] === id) { idx = j; break; } }
      if (idx < 0) { return; }
      for (j = 0; j < stepEls.length; j++) {
        if (j === idx) { addClass(stepEls[j], "active"); }
        else { removeClass(stepEls[j], "active"); }
      }
      current = id;
      renderNav(idx);
      if (end) {
        if (idx === ids.length - 1) {
          addClass(end, "show");
          if (readMark) { readMark.removeAttribute("hidden"); }
        } else { removeClass(end, "show"); }
      }
      if (save && !reviewMode) {
        ensureLesson(lessonId).lastStepId = id;
        state.lastLocation = { lessonId: lessonId, stepId: id };
        persist();
      }
      h = stepEls[idx].querySelector("h2.step-title");
      if (h && h.focus) { try { h.focus(); } catch (e) {} }
      top = 0; n = stepEls[idx];
      while (n) { top += (n.offsetTop || 0); n = n.offsetParent; }
      try { window.scrollTo(0, Math.max(0, top - 8)); } catch (e) {}
    }

    var initial = ids[0];
    var hsh = (window.location.hash || "").replace(/^#/, "");
    var saved = (!reviewMode && state.lessons[lessonId]) ? state.lessons[lessonId].lastStepId : null;
    if (hsh && prlInArray(ids, hsh)) { initial = hsh; }
    else if (saved && prlInArray(ids, saved)) { initial = saved; }
    if (window.history && window.history.replaceState) {
      try { window.history.replaceState(null, "", "#" + initial); } catch (e) {}
    }
    addClass(root, "js-step");
    show(initial, true);
    if ("onhashchange" in window) {
      window.onhashchange = function () {
        var hh = (window.location.hash || "").replace(/^#/, "");
        if (hh && hh !== current && prlInArray(ids, hh)) { show(hh, true); }
      };
    }
  }

  function initReveal(article) {
    var blocks = article.querySelectorAll(".reveal"), i;
    for (i = 0; i < blocks.length; i++) {
      (function (block) {
        var btn = block.querySelector(".reveal-btn");
        if (!btn) { return; }
        btn.setAttribute("aria-expanded", "false");
        btn.onclick = function () {
          var open = (" " + block.className + " ").indexOf(" open ") >= 0;
          if (open) {
            removeClass(block, "open");
            btn.setAttribute("aria-expanded", "false");
          } else {
            addClass(block, "open");
            btn.setAttribute("aria-expanded", "true");
          }
        };
      })(blocks[i]);
    }
    if (blocks.length) { addClass(root, "js-reveal"); }
  }

  function initQuiz(qz, lessonId, reviewMode) {
    var qid = qz.getAttribute("data-question-id");
    if (!qid) { return; }
    var qrev = parseInt(qz.getAttribute("data-question-revision") || "1", 10);
    var correctOpt = qz.getAttribute("data-correct-option");
    var stepEl = closestTag(qz, "section", "step");
    var stepId = stepEl ? stepEl.id : "";
    var form = qz.querySelector(".quiz-form");
    var radios = form ? form.querySelectorAll('input[type="radio"]') : [];
    var hint = qz.querySelector(".quiz-hint");
    var submitBtn = qz.querySelector(".quiz-submit");
    var result = qz.querySelector(".quiz-result");
    var verdict = qz.querySelector(".quiz-verdict");
    var retryBtn = qz.querySelector(".quiz-retry");
    var backLink = qz.querySelector(".quiz-back-review");
    var answerZone = qz.querySelector(".answer-zone");
    var optLis = qz.querySelectorAll(".quiz-opt-explains li");
    var submitted = false;

    function showHint(msg) {
      if (hint) { hint.textContent = msg; addClass(hint, "show"); }
    }
    function hideHint() {
      if (hint) { hint.textContent = ""; removeClass(hint, "show"); }
    }
    function markCorrectOpt() {
      var i, li, tag;
      for (i = 0; i < optLis.length; i++) {
        li = optLis[i];
        if (li.getAttribute("data-opt") === correctOpt) {
          addClass(li, "is-correct");
          tag = doc.createElement("span");
          tag.className = "correct-tag";
          tag.textContent = "正确";
          li.insertBefore(tag, li.firstChild);
        }
      }
    }
    function unmarkCorrectOpt() {
      var tags = qz.querySelectorAll(".correct-tag"), t, u;
      for (t = 0; t < tags.length; t++) {
        if (tags[t].parentNode) { tags[t].parentNode.removeChild(tags[t]); }
      }
      var lis = qz.querySelectorAll(".quiz-opt-explains li.is-correct");
      for (u = 0; u < lis.length; u++) { removeClass(lis[u], "is-correct"); }
    }
    function setLocked(locked) {
      var i;
      for (i = 0; i < radios.length; i++) { radios[i].disabled = locked; }
      if (submitBtn) { submitBtn.disabled = locked; }
    }
    function renderSubmitted(sel, ok) {
      var i;
      submitted = true;
      setLocked(true);
      hideHint();
      for (i = 0; i < radios.length; i++) {
        if (radios[i].value === sel) { radios[i].checked = true; }
      }
      if (verdict) {
        verdict.textContent = ok ? "回答正确" : "回答错误";
        removeClass(verdict, "correct"); removeClass(verdict, "wrong");
        addClass(verdict, ok ? "correct" : "wrong");
      }
      if (result) { addClass(result, "show"); }
      if (answerZone) { addClass(answerZone, "show"); }
      unmarkCorrectOpt();
      markCorrectOpt();
    }

    var rec = state.questions[qid];
    if (rec && rec.revision === qrev && typeof rec.lastOptionId === "string") {
      renderSubmitted(rec.lastOptionId, rec.lastCorrect === true);
    } else if (rec && rec.revision !== qrev) {
      showHint("题目已更新，需重新作答。");
    }

    if (submitBtn) {
      submitBtn.onclick = function () {
        var sel = null, i, ok, old, fresh;
        if (submitted) { return; }
        for (i = 0; i < radios.length; i++) {
          if (radios[i].checked) { sel = radios[i].value; break; }
        }
        if (sel === null) { showHint("请先选择一个选项，再提交答案。"); return; }
        ok = (sel === correctOpt);
        old = state.questions[qid];
        fresh = (!old) || (old.revision !== qrev);
        if (fresh) {
          state.questions[qid] = {
            revision: qrev, attempts: 1, wrongAttempts: ok ? 0 : 1,
            lastOptionId: sel, lastCorrect: ok, needsReview: !ok,
            lessonId: lessonId, stepId: stepId
          };
        } else {
          old.attempts = (old.attempts || 0) + 1;
          if (!ok) { old.wrongAttempts = (old.wrongAttempts || 0) + 1; }
          old.lastOptionId = sel;
          old.lastCorrect = ok;
          old.needsReview = !ok;
          old.lessonId = lessonId;
          old.stepId = stepId;
        }
        persist();
        renderSubmitted(sel, ok);
        if (reviewMode && backLink) {
          backLink.setAttribute("href", basePath + "review.html");
          backLink.removeAttribute("hidden");
        }
      };
    }
    if (retryBtn) {
      retryBtn.onclick = function () {
        var i;
        for (i = 0; i < radios.length; i++) { radios[i].checked = false; }
        setLocked(false);
        submitted = false;
        unmarkCorrectOpt();
        if (result) { removeClass(result, "show"); }
        if (answerZone) { removeClass(answerZone, "show"); }
        if (backLink) { backLink.setAttribute("hidden", "hidden"); }
        hideHint();
      };
    }
  }

  function initQuizAll(article, lessonId, reviewMode) {
    var quizzes = article.querySelectorAll(".quiz"), i;
    for (i = 0; i < quizzes.length; i++) { initQuiz(quizzes[i], lessonId, reviewMode); }
    if (quizzes.length) { addClass(root, "js-quiz"); }
  }

  function initProgress(article, lessonId) {
    var markBtn = doc.getElementById("mark-read");
    var readState = article.querySelector(".read-state");
    function refresh() {
      var rec = ensureLesson(lessonId);
      if (markBtn) { markBtn.textContent = rec.completed ? "取消已读" : "标记为已读"; }
      if (readState) { readState.textContent = rec.completed ? "已标记为已读" : "尚未标记为已读"; }
    }
    if (markBtn) {
      markBtn.onclick = function () {
        var rec = ensureLesson(lessonId);
        rec.completed = !rec.completed;
        persist();
        refresh();
      };
    }
    var cb = article.querySelector(".practice-done");
    var hasPractice = article.querySelector('section.step[data-step-type="practice"]');
    if (cb && hasPractice) {
      var rec0 = state.lessons[lessonId];
      cb.checked = !!(rec0 && rec0.practiceDone);
      cb.onchange = function () {
        ensureLesson(lessonId).practiceDone = !!cb.checked;
        persist();
      };
    }
    refresh();
  }

  function initLessonPage() {
    if (!hasPage("page-lesson")) { return; }
    var article = doc.querySelector("article.lesson");
    if (!article) { return; }
    var lessonId = article.getAttribute("data-lesson-id") || "";
    var reviewMode = isReviewMode();
    initSteps(article, lessonId, reviewMode);
    initReveal(article);
    initQuizAll(article, lessonId, reviewMode);
    initProgress(article, lessonId);
  }

  function initHomePage() {
    if (!hasPage("page-index")) { return; }
    var order = doc.getElementById("lesson-order");
    if (!order) { return; }
    var items = order.querySelectorAll("li[data-lesson-id]"), i, id, rec, st;
    var read = 0, firstOpen = null;
    for (i = 0; i < items.length; i++) {
      id = items[i].getAttribute("data-lesson-id");
      rec = state.lessons[id];
      st = items[i].querySelector(".lesson-status");
      if (rec && rec.completed) {
        read++;
        if (st) { st.textContent = "已读"; }
      } else {
        if (firstOpen === null) { firstOpen = id; }
        if (st) { st.textContent = rec ? "学习中" : "未开始"; }
      }
    }
    var elRead = doc.getElementById("stat-read");
    if (elRead) { elRead.textContent = String(read); }
    var elReview = doc.getElementById("stat-review");
    if (elReview) { elReview.textContent = String(countReview()); }
    var primary = doc.getElementById("home-primary");
    if (primary) {
      var href = basePath + "course.html";
      var label = "重新查看课程";
      var loc = state.lastLocation;
      if (loc && loc.lessonId && state.lessons[loc.lessonId] && state.lessons[loc.lessonId].completed !== true) {
        href = basePath + "lessons/" + loc.lessonId + ".html#" + loc.stepId;
        label = "继续学习";
      } else if (firstOpen !== null) {
        href = basePath + "lessons/" + firstOpen + ".html";
        label = (read === 0) ? "开始学习" : "继续学习";
      }
      primary.setAttribute("href", href);
      primary.textContent = label;
    }
  }

  function initCoursePage() {
    if (!hasPage("page-course")) { return; }
    var items = doc.querySelectorAll("li[data-lesson-id]"), i;
    for (i = 0; i < items.length; i++) {
      (function (li) {
        var id = li.getAttribute("data-lesson-id");
        var rec = state.lessons[id];
        var st = li.querySelector(".lesson-status");
        if (st) { st.textContent = (!rec) ? "未开始" : (rec.completed ? "已读" : "学习中"); }
      })(items[i]);
    }
    var practs = doc.querySelectorAll("li[data-practice-for]"), j;
    for (j = 0; j < practs.length; j++) {
      (function (li) {
        var id = li.getAttribute("data-practice-for");
        var rec = state.lessons[id];
        var st = li.querySelector(".practice-status");
        if (st) { st.textContent = (rec && rec.practiceDone) ? "已完成" : "未完成"; }
      })(practs[j]);
    }
  }

  function initReviewPage() {
    if (!hasPage("page-review")) { return; }
    var index = doc.getElementById("review-index");
    var list = doc.getElementById("review-list");
    var empty = doc.getElementById("review-empty");
    if (!index || !list) { return; }
    var items = index.querySelectorAll("li[data-question-id]"), i, li, qid, rec;
    var entries = [], seen = {};
    for (i = 0; i < items.length; i++) {
      li = items[i];
      qid = li.getAttribute("data-question-id");
      if (!qid || seen[qid]) { continue; }
      rec = state.questions[qid];
      if (!rec) { continue; }
      var revAttr = li.getAttribute("data-question-revision");
      var mismatch = (revAttr !== null && revAttr !== "" && parseInt(revAttr, 10) !== rec.revision);
      if (rec.needsReview === true || mismatch) {
        seen[qid] = true;
        entries.push({
          lessonId: li.getAttribute("data-lesson-id") || "",
          stepId: li.getAttribute("data-step-id") || "",
          lessonTitle: li.getAttribute("data-lesson-title") || "",
          stepTitle: li.getAttribute("data-step-title") || "",
          updated: mismatch
        });
      }
    }
    clearChildren(list);
    if (!entries.length) {
      if (empty) { empty.removeAttribute("hidden"); }
      return;
    }
    if (empty) { empty.setAttribute("hidden", "hidden"); }
    var PAGE = 10, page = 0;
    var pager = doc.createElement("div");
    pager.className = "review-pager";
    function render() {
      var k, totalPages, item, a, info, prevB, nextB;
      clearChildren(list);
      clearChildren(pager);
      for (k = page * PAGE; k < Math.min(page * PAGE + PAGE, entries.length); k++) {
        item = doc.createElement("li");
        a = doc.createElement("a");
        a.setAttribute("href", basePath + "lessons/" + entries[k].lessonId + ".html?review=1#" + entries[k].stepId);
        a.textContent = entries[k].lessonTitle + " · " + entries[k].stepTitle +
          (entries[k].updated ? "（题目已更新，需重新作答）" : "");
        item.appendChild(a);
        list.appendChild(item);
      }
      totalPages = Math.ceil(entries.length / PAGE);
      if (totalPages > 1) {
        info = doc.createElement("span");
        info.className = "pager-info";
        info.textContent = "第 " + (page + 1) + " / " + totalPages + " 页";
        prevB = doc.createElement("button");
        prevB.type = "button"; prevB.textContent = "上一页";
        nextB = doc.createElement("button");
        nextB.type = "button"; nextB.textContent = "下一页";
        if (page <= 0) { prevB.setAttribute("disabled", "disabled"); }
        if (page >= totalPages - 1) { nextB.setAttribute("disabled", "disabled"); }
        prevB.onclick = function () { if (page > 0) { page--; render(); } };
        nextB.onclick = function () { if (page < totalPages - 1) { page++; render(); } };
        pager.appendChild(prevB); pager.appendChild(info); pager.appendChild(nextB);
      }
    }
    render();
    if (pager.childNodes.length && list.parentNode) {
      list.parentNode.insertBefore(pager, list.nextSibling);
    }
  }

  var IMPORT_ERRORS = {
    "too-large": "备份文本超过 128 KiB，无法导入。原记录未受影响。",
    "invalid-json": "备份文本不是有效的 JSON。原记录未受影响。",
    "unsafe-keys": "备份包含不安全的键，已拒绝。原记录未受影响。",
    "unknown-version": "备份的版本不受支持。原记录未受影响。",
    "course-mismatch": "备份的课程 ID 不匹配。原记录未受影响。",
    "bad-fields": "备份字段类型或范围不正确。原记录未受影响。"
  };

  function catalogIds(listId) {
    var ol = doc.getElementById(listId), out = [], items, i, id;
    if (!ol) { return out; }
    items = ol.querySelectorAll("li");
    for (i = 0; i < items.length; i++) {
      id = items[i].getAttribute("data-lesson-id") || items[i].getAttribute("data-question-id");
      if (id) { out.push(id); }
    }
    return out;
  }

  function showCorruptTools() {
    var box = doc.getElementById("import-preview");
    if (!box) { return; }
    box.removeAttribute("hidden");
    var p = doc.createElement("p");
    p.textContent = "检测到已保存的学习数据损坏或版本未知，未自动覆盖。你可以查看原始文本，再决定是否显式重置。";
    var pre = doc.createElement("pre");
    pre.className = "raw-backup";
    pre.style.display = "none";
    pre.textContent = corruptRaw || "";
    var viewBtn = doc.createElement("button");
    viewBtn.type = "button"; viewBtn.textContent = "查看原始文本";
    viewBtn.onclick = function () {
      pre.style.display = (pre.style.display === "none") ? "block" : "none";
    };
    var resetBtn = doc.createElement("button");
    resetBtn.type = "button"; resetBtn.textContent = "显式重置（清空损坏数据）";
    resetBtn.onclick = function () {
      if (!window.confirm("确定清空损坏的学习数据吗？字号设置将保留。")) { return; }
      wipeKeepingFontSize();
    };
    box.appendChild(p); box.appendChild(viewBtn); box.appendChild(resetBtn); box.appendChild(pre);
  }

  function initSettingsPage() {
    if (!hasPage("page-settings")) { return; }
    var status = doc.getElementById("storage-status");
    if (status) {
      if (corruptMode) {
        status.textContent = "本地保存：已存数据损坏或版本未知，未自动覆盖。可在下方查看原始文本或显式重置。";
      } else if (storageOk) {
        status.textContent = "本地保存：可用。";
      } else {
        status.textContent = "本地保存：不可用。刷新或跨页面后，临时记录可能丢失。";
      }
    }
    var exportBtn = doc.getElementById("export-btn");
    var exportText = doc.getElementById("export-text");
    if (exportBtn && exportText) {
      exportBtn.onclick = function () {
        exportText.value = JSON.stringify(state, null, 2);
      };
    }
    var importText = doc.getElementById("import-text");
    var importBtn = doc.getElementById("import-btn");
    var importPreview = doc.getElementById("import-preview");
    if (importBtn && importText && importPreview) {
      importBtn.onclick = function () {
        var res = validateBackupText(importText.value, {
          courseId: courseId, maxBytes: 131072,
          catalogLessons: catalogIds("catalog-lessons"),
          catalogQuestions: catalogIds("catalog-questions")
        });
        var p = doc.createElement("p");
        clearChildren(importPreview);
        importPreview.removeAttribute("hidden");
        if (!res.ok) {
          p.textContent = IMPORT_ERRORS[res.error] || "备份无效，未导入。原记录未受影响。";
          importPreview.appendChild(p);
          return;
        }
        p.textContent = "将恢复 " + res.preview.read + " 节已读、" +
          res.preview.review + " 道待复习题目。导入将整体替换当前记录（不合并）。";
        importPreview.appendChild(p);
        var okBtn = doc.createElement("button");
        okBtn.type = "button";
        okBtn.textContent = "确认导入";
        okBtn.onclick = function () {
          if (!window.confirm("确定用备份整体替换当前学习记录吗？")) { return; }
          state = normalizeState(res.state);
          corruptMode = false;
          persist(true);
          window.location.reload();
        };
        importPreview.appendChild(okBtn);
      };
    }
    var clearBtn = doc.getElementById("clear-btn");
    if (clearBtn) {
      clearBtn.onclick = function () {
        if (!window.confirm("确定清除本课程的学习记录吗？字号设置将保留。")) { return; }
        wipeKeepingFontSize();
      };
    }
    if (corruptMode) { showCorruptTools(); }
  }

  addClass(root, "js");
  loadState();
  if (!storageOk || corruptMode) { showBanner(); }
  applyFontSize(state.settings.fontSize);
  bindFontRadios();
  try { initLessonPage(); } catch (e) {}
  try { initHomePage(); } catch (e) {}
  try { initCoursePage(); } catch (e) {}
  try { initReviewPage(); } catch (e) {}
  try { initSettingsPage(); } catch (e) {}
}
