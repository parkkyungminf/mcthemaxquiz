// M.C THE MAX 초성퀴즈 - Quiz interaction
(function () {
    const form = document.getElementById("answer-form");
    const resultPanel = document.getElementById("result-panel");
    const resultContent = document.getElementById("result-content");
    const submitBtn = document.getElementById("submit-btn");
    const skipBtn = document.getElementById("skip-btn");
    const nextBtn = document.getElementById("next-btn");

    if (!form) return;

    function submitAnswer(e) {
        if (e) e.preventDefault();

        const formData = new FormData(form);

        fetch("/quiz/answer", {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: formData,
        })
            .then((r) => r.json())
            .then((data) => {
                showResult(data);
            })
            .catch(() => {
                form.submit();
            });
    }

    function esc(str) {
        const d = document.createElement("div");
        d.textContent = str;
        return d.innerHTML;
    }

    function showResult(data) {
        form.style.display = "none";
        resultPanel.classList.remove("hidden");

        const emoji = data.correct ? "\ud83d\ude03" : "\ud83e\udd72";
        const scoreClass = data.correct ? "good" : "bad";

        resultContent.innerHTML = `
            <div class="result-emoji">${emoji}</div>
            <div class="score-line ${scoreClass}">${data.correct ? "정답!" : "오답"} +${data.score}점</div>
            <div class="answer-detail">
                <div>정답: <strong>${esc(data.correct_title)}</strong></div>
                ${data.user_title ? '<div>내 답: ' + esc(data.user_title) + '</div>' : ''}
                <div style="margin-top:8px">가사: <strong>${esc(data.correct_lyrics).replace(/\n/g, '<br>')}</strong></div>
            </div>
        `;
    }

    form.addEventListener("submit", submitAnswer);

    skipBtn.addEventListener("click", function () {
        document.getElementById("title").value = "";
        submitAnswer(null);
    });

    nextBtn.addEventListener("click", function () {
        window.location.href = "/quiz/question";
    });

    document.getElementById("title").addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            submitAnswer(null);
        }
    });
})();
