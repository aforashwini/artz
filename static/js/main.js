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
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    function handleFile(file) {
        selectedFile = file;
        selectedSample = null;
        const url = URL.createObjectURL(file);
        previewImg.src = url;
        previewArea.classList.remove("hidden");
    }

    // --- Samples ---
    document.querySelectorAll(".sample-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            selectedSample = btn.dataset.sample;
            selectedFile = null;
            previewImg.src = `/samples/${selectedSample}`;
            previewArea.classList.remove("hidden");
        });
    });

    // --- Analyze ---
    analyzeBtn.addEventListener("click", () => {
        if (!selectedFile && !selectedSample) return;

        uploadSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        resultsSection.classList.add("hidden");

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
                loadingSection.classList.add("hidden");
                renderResults(data);
                resultsSection.classList.remove("hidden");
            })
            .catch((err) => {
                loadingSection.classList.add("hidden");
                uploadSection.classList.remove("hidden");
                const msg = err.error || "Something went wrong. Please try again.";
                alert("Analysis Error: " + msg);
            });
    });

    // --- Render Results ---
    function renderResults(data) {
        // Overview image
        overviewImg.src = data.overview;

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

        overviewStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">Pattern Pieces Detected</div>
                <div class="stat-value">${data.piece_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Average Waste Factor</div>
                <div class="stat-value ${parseFloat(avgWaste) > 15 ? 'warn' : 'good'}">${avgWaste}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Optimization Suggestions</div>
                <div class="stat-value">${totalSuggestions}</div>
            </div>
        `;

        // Suggestions per piece
        suggestionsContainer.innerHTML = "";
        data.pieces.forEach((piece) => {
            const section = document.createElement("div");
            section.className = "card piece-section";

            const badgeClass = piece.is_inefficient ? "inefficient" : "efficient";
            const badgeText = piece.is_inefficient ? "Needs Optimization" : "Efficient";

            let metricsHTML = `
                <div class="metric-chip"><strong>Area:</strong> ${piece.area.toLocaleString()} px²</div>
                <div class="metric-chip"><strong>Waste Factor:</strong> ${piece.waste_factor}%</div>
                <div class="metric-chip"><strong>BBox Utilization:</strong> ${piece.bbox_utilization}%</div>
            `;

            let suggestionsHTML = "";
            piece.suggestions.forEach((s) => {
                suggestionsHTML += `
                    <div class="suggestion-card">
                        <div class="suggestion-card-header" style="background: ${s.color}15; border-left: 4px solid ${s.color};">
                            <span class="suggestion-title">${s.title}</span>
                            <span class="impact-badge" style="background: ${s.color};">${s.impact}</span>
                        </div>
                        <div class="suggestion-card-body">
                            <img src="${s.image}" alt="${s.title}">
                            <div class="suggestion-text">
                                <p>${s.description}</p>
                                <span class="savings-tag" style="background: ${s.color}20; color: ${s.color};">
                                    Projected Savings: ${s.savings_pct}% fabric reduction
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            });

            if (piece.suggestions.length === 0) {
                suggestionsHTML = `<p class="muted">This piece is already well-optimized. No suggestions needed.</p>`;
            }

            section.innerHTML = `
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

    // --- Reset ---
    resetBtn.addEventListener("click", () => {
        resultsSection.classList.add("hidden");
        uploadSection.classList.remove("hidden");
        previewArea.classList.add("hidden");
        selectedFile = null;
        selectedSample = null;
        fileInput.value = "";
    });
});
