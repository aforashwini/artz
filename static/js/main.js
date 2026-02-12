document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const previewArea = document.getElementById("preview-area");
    const previewImg = document.getElementById("preview-img");
    const analyzeBtn = document.getElementById("analyze-btn");
    const uploadSection = document.getElementById("upload-section");
    const loadingSection = document.getElementById("loading-section");
    const resultsSection = document.getElementById("results-section");
    const overviewImg = document.getElementById("overview-img");
    const overviewStats = document.getElementById("overview-stats");
    const suggestionsContainer = document.getElementById("suggestions-container");
    const resetBtn = document.getElementById("reset-btn");

    let selectedFile = null;
    let selectedSample = null;

    // --- Drop Zone ---
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
        selectedFile = file;
        selectedSample = null;
        document.querySelectorAll(".sample-btn").forEach((b) => b.classList.remove("selected"));
        previewImg.src = URL.createObjectURL(file);
        previewArea.classList.remove("hidden");
    }

    // --- Samples ---
    document.querySelectorAll(".sample-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            selectedSample = btn.dataset.sample;
            selectedFile = null;
            document.querySelectorAll(".sample-btn").forEach((b) => b.classList.remove("selected"));
            btn.classList.add("selected");
            previewImg.src = `/samples/${selectedSample}`;
            previewArea.classList.remove("hidden");
        });
    });

    // --- Loading steps ---
    let stepInterval = null;

    function startLoadingSteps() {
        const steps = ["step-detect", "step-analyze", "step-suggest", "step-render"];
        let current = 0;
        steps.forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.classList.remove("active", "done");
        });
        const first = document.getElementById(steps[0]);
        if (first) first.classList.add("active");

        stepInterval = setInterval(() => {
            const prev = document.getElementById(steps[current]);
            if (prev) {
                prev.classList.remove("active");
                prev.classList.add("done");
            }
            current++;
            if (current < steps.length) {
                const next = document.getElementById(steps[current]);
                if (next) next.classList.add("active");
            } else {
                clearInterval(stepInterval);
            }
        }, 800);
    }

    function stopLoadingSteps() {
        if (stepInterval) {
            clearInterval(stepInterval);
            stepInterval = null;
        }
        ["step-detect", "step-analyze", "step-suggest", "step-render"].forEach((id) => {
            const el = document.getElementById(id);
            if (el) {
                el.classList.remove("active");
                el.classList.add("done");
            }
        });
    }

    // --- Analyze ---
    analyzeBtn.addEventListener("click", () => {
        if (!selectedFile && !selectedSample) return;

        uploadSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        resultsSection.classList.add("hidden");

        startLoadingSteps();

        const formData = new FormData();
        if (selectedFile) {
            formData.append("file", selectedFile);
        } else {
            formData.append("sample", selectedSample);
        }

        fetch("/analyze", { method: "POST", body: formData })
            .then((res) => {
                if (!res.ok) return res.json().then((d) => Promise.reject(d));
                return res.json();
            })
            .then((data) => {
                stopLoadingSteps();
                setTimeout(() => {
                    loadingSection.classList.add("hidden");
                    renderResults(data);
                    resultsSection.classList.remove("hidden");
                }, 400);
            })
            .catch((err) => {
                stopLoadingSteps();
                loadingSection.classList.add("hidden");
                uploadSection.classList.remove("hidden");
                showError(err.error || "Something went wrong. Please try again.");
            });
    });

    // --- Error toast ---
    function showError(msg) {
        const toast = document.createElement("div");
        toast.className = "error-toast";
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // --- Render Results ---
    function renderResults(data) {
        // Overview
        if (data.overview) {
            overviewImg.src = data.overview;
            overviewImg.style.display = "";
        } else {
            overviewImg.style.display = "none";
        }

        // Stats
        let totalWaste = 0;
        let totalSuggestions = 0;
        data.pieces.forEach((p) => {
            totalWaste += p.waste_factor;
            totalSuggestions += p.suggestions.length;
        });
        const avgWaste = data.pieces.length > 0
            ? (totalWaste / data.pieces.length).toFixed(1)
            : 0;
        const wasteClass = parseFloat(avgWaste) > 15 ? "warn" : "good";

        overviewStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">PIECES DETECTED</div>
                <div class="stat-value">${data.piece_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">AVG WASTE FACTOR</div>
                <div class="stat-value ${wasteClass}">${avgWaste}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">OPTIMIZATIONS</div>
                <div class="stat-value">${totalSuggestions}</div>
            </div>
        `;

        // Suggestions per piece
        suggestionsContainer.innerHTML = "";
        data.pieces.forEach((piece, pieceIdx) => {
            const section = document.createElement("div");
            section.className = "card piece-section fade-in";
            section.style.animationDelay = `${pieceIdx * 0.1}s`;

            const badgeClass = piece.is_inefficient ? "inefficient" : "efficient";
            const badgeText = piece.is_inefficient ? "OPTIMIZE" : "EFFICIENT";

            let metricsHTML = `
                <div class="metric-chip"><strong>AREA:</strong> ${piece.area.toLocaleString()} px\u00B2</div>
                <div class="metric-chip"><strong>WASTE:</strong> ${piece.waste_factor}%</div>
                <div class="metric-chip"><strong>BBOX UTIL:</strong> ${piece.bbox_utilization}%</div>
            `;

            let suggestionsHTML = "";
            piece.suggestions.forEach((s, sIdx) => {
                const bgTint = hexToRgba(s.color, 0.06);
                const borderTint = hexToRgba(s.color, 0.2);

                const imgHTML = s.image
                    ? `<img src="${s.image}" alt="${s.title}">`
                    : `<div class="suggestion-img-placeholder">
                         <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                           <rect x="2" y="2" width="28" height="28" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 2" fill="none"/>
                           <path d="M10 16h12M16 10v12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                         </svg>
                         <small>Diagram unavailable</small>
                       </div>`;

                suggestionsHTML += `
                    <div class="suggestion-card">
                        <div class="suggestion-card-header" style="background: ${bgTint}; border-left: 3px solid ${s.color};">
                            <span class="suggestion-title">${s.title}</span>
                            <span class="impact-badge" style="background: ${bgTint}; color: ${s.color}; border: 1px solid ${borderTint};">${s.impact}</span>
                        </div>
                        <div class="suggestion-card-body">
                            ${imgHTML}
                            <div class="suggestion-text">
                                <p>${s.description}</p>
                                <span class="savings-tag" style="background: ${bgTint}; color: ${s.color}; border-color: ${borderTint};">
                                    PROJECTED SAVINGS: ${s.savings_pct}% FABRIC REDUCTION
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            });

            if (piece.suggestions.length === 0) {
                suggestionsHTML = `
                    <div style="text-align: center; padding: 24px; color: #059669; font-size: 0.85rem; letter-spacing: 1px; font-weight: 600;">
                        This piece is optimally efficient. No modifications needed.
                    </div>
                `;
            }

            section.innerHTML = `
                <div class="card-label">PIECE ANALYSIS</div>
                <div class="piece-header">
                    <h3>${piece.label}</h3>
                    <span class="badge ${badgeClass}">${badgeText}</span>
                </div>
                <div class="piece-metrics">${metricsHTML}</div>
                <div class="suggestion-cards">${suggestionsHTML}</div>
            `;

            suggestionsContainer.appendChild(section);
        });
    }

    function hexToRgba(hex, alpha) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        if (result) {
            return `rgba(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}, ${alpha})`;
        }
        return `rgba(91, 33, 182, ${alpha})`;
    }

    // --- Reset ---
    resetBtn.addEventListener("click", () => {
        resultsSection.classList.add("hidden");
        uploadSection.classList.remove("hidden");
        uploadSection.classList.add("fade-in");
        previewArea.classList.add("hidden");
        selectedFile = null;
        selectedSample = null;
        fileInput.value = "";
        document.querySelectorAll(".sample-btn").forEach((b) => b.classList.remove("selected"));
    });
});
