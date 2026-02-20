// MC THE MAX 초성퀴즈 - Quiz interaction
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
                // Fallback to normal form submit
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

        const scoreClass =
            data.total_score >= 75 ? "good" : data.total_score >= 25 ? "ok" : "bad";
        const titleIcon =
            data.title_match === "exact" ? "correct" : "wrong";
        const lyricsIcon =
            data.lyrics_match === "exact"
                ? "correct"
                : data.lyrics_match === "partial"
                    ? "partial"
                    : "wrong";

        resultContent.innerHTML = `
            <div class="score-line ${scoreClass}">+${data.total_score}점</div>
            <div class="answer-detail">
                <div>곡명 정답: <strong>${esc(data.correct_title)}</strong></div>
                <div>내 답: <span class="${titleIcon}">${esc(data.user_title) || "(미입력)"}</span>
                    → <span class="${titleIcon}">+${data.title_score}</span></div>
                <div style="margin-top:8px">가사 정답: <strong>${esc(data.correct_lyrics)}</strong></div>
                <div>내 답: <span class="${lyricsIcon}">${esc(data.user_lyrics) || "(미입력)"}</span>
                    → <span class="${lyricsIcon}">+${data.lyrics_score}</span></div>
            </div>
        `;
    }

    form.addEventListener("submit", submitAnswer);

    skipBtn.addEventListener("click", function () {
        document.getElementById("title").value = "";
        document.getElementById("lyrics").value = "";
        submitAnswer(null);
    });

    nextBtn.addEventListener("click", function () {
        window.location.href = "/quiz/question";
    });

    // Enter key on lyrics field submits
    document.getElementById("lyrics").addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            submitAnswer(null);
        }
    });

    // Tab from title to lyrics
    document.getElementById("title").addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            document.getElementById("lyrics").focus();
        }
    });
})();
