/* 备份校验 node 驱动：被 tests/test_backup.py 调用。
 * 用 require 加载 assets/reader.js 的 validateBackupText，对
 * 各类备份输入做判定，把结果以 JSON 输出到 stdout。
 * 注意：本文件只做测试调用，不参与构建产物。
 */
"use strict";

var path = require("path");
var validateBackupText =
  require(path.join(__dirname, "..", "assets", "reader.js")).validateBackupText;

var results = [];
function check(name, fn) {
  try {
    results.push({ name: name, pass: !!fn() });
  } catch (e) {
    results.push({ name: name, pass: false, error: String(e && e.stack || e) });
  }
}

function baseState() {
  return {
    schemaVersion: 1,
    courseId: "python-relearn",
    settings: { fontSize: 26 },
    lastLocation: { lessonId: "run-and-bindings", stepId: "s-quiz-1" },
    lessons: {
      "run-and-bindings": {
        lastStepId: "s-quiz-1",
        completed: true,
        practiceDone: false
      }
    },
    questions: {
      "run-and-bindings-q1": {
        revision: 1,
        attempts: 1,
        wrongAttempts: 1,
        lastOptionId: "b",
        lastCorrect: false,
        needsReview: true,
        lessonId: "run-and-bindings",
        stepId: "s-quiz-1"
      }
    }
  };
}

var opts = {
  courseId: "python-relearn",
  catalogLessons: ["run-and-bindings"],
  catalogQuestions: ["run-and-bindings-q1"]
};

check("valid", function () {
  var r = validateBackupText(JSON.stringify(baseState()), opts);
  return r.ok === true &&
    r.preview.read === 1 &&
    r.preview.review === 1;
});

check("too-large", function () {
  var big = new Array(200000).join("x"); // 约 200KiB > 128KiB
  return validateBackupText(big, opts).error === "too-large";
});

check("invalid-json", function () {
  return validateBackupText("{not json", opts).error === "invalid-json";
});

check("unsafe-keys", function () {
  var text = '{"schemaVersion":1,"courseId":"python-relearn",' +
    '"settings":{"fontSize":26},"lastLocation":null,' +
    '"lessons":{},"questions":{},"__proto__":{"polluted":true}}';
  return validateBackupText(text, opts).error === "unsafe-keys";
});

check("unknown-version", function () {
  var s = baseState();
  s.schemaVersion = 2;
  return validateBackupText(JSON.stringify(s), opts).error === "unknown-version";
});

check("course-mismatch", function () {
  var s = baseState();
  s.courseId = "other-course";
  return validateBackupText(JSON.stringify(s), opts).error === "course-mismatch";
});

check("bad-fields-fontsize", function () {
  var s = baseState();
  s.settings.fontSize = 25; // 不在 22/26/30 三档
  return validateBackupText(JSON.stringify(s), opts).error === "bad-fields";
});

check("bad-fields-attempts", function () {
  var s = baseState();
  s.questions["run-and-bindings-q1"].attempts = -1;
  return validateBackupText(JSON.stringify(s), opts).error === "bad-fields";
});

console.log(JSON.stringify(results));
