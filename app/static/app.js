async function loadDashboard() {
    try {
        const res = await fetch("/api/dashboard");
        const data = await res.json();

        // 1. Recovery
        const score = data.habits.recovery_score || 80;
        document.getElementById("recovery-score").textContent = `${score}/100`;
        const readiness = score >= 85 ? "🔥 Prime for Overload" : score >= 65 ? "⚡ Moderate Recovery" : "⚠️ Recovery Deficit";
        document.getElementById("recovery-readiness").textContent = readiness;

        // 2. Protein
        const protein = data.habits.protein_grams || 0;
        const target = 160;
        document.getElementById("protein-val").textContent = `${protein}g`;
        const pct = Math.min(100, Math.round((protein / target) * 100));
        document.getElementById("protein-bar").style.width = `${pct}%`;
        document.getElementById("protein-target").textContent = `${pct}% of ${target}g goal`;

        // 3. BMI
        const m = data.metrics;
        document.getElementById("bmi-val").textContent = m.bmi ? m.bmi : "—";
        document.getElementById("bmi-category").textContent = `${m.bmi_category || "Normal"} (${m.height_cm}cm · ${m.weight_kg}kg)`;

        // 4. Overload stats
        document.getElementById("overload-count").textContent = `${data.summary.overload_sets} Sets`;
        document.getElementById("total-sets").textContent = `${data.summary.total_logged_sets} total · ${data.summary.total_volume_kg}kg vol`;

        // Fill inputs with current values
        document.getElementById("protein-input").value = data.habits.protein_grams || 150;
        document.getElementById("water-input").value = data.habits.water_liters || 3.0;
        document.getElementById("sleep-input").value = data.habits.sleep_hours || 7.5;
        document.getElementById("height-input").value = m.height_cm || 178;
        document.getElementById("weight-input").value = m.weight_kg || 75.0;

        // Workouts table
        const tbody = document.getElementById("workout-tbody");
        if (!data.workouts || data.workouts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading-td">No workouts logged yet. Log your first set above!</td></tr>';
            return;
        }

        tbody.innerHTML = data.workouts.map(w => {
            const dateStr = new Date(w.created_at).toLocaleDateString("en-IN", {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
            });
            const badgeClass = w.is_overload ? "badge-overload" : "badge-maintenance";
            return `
                <tr>
                    <td><strong>${w.exercise_name}</strong></td>
                    <td><span style="color: #94a3b8">${w.muscle_group}</span></td>
                    <td><strong style="color: #00f0ff">${w.weight_kg} kg</strong> × ${w.reps}</td>
                    <td>${w.estimated_1rm} kg</td>
                    <td><span class="${badgeClass}">${w.overload_badge || "Logged"}</span></td>
                    <td style="color: #64748b">${dateStr}</td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        console.error("Failed to load dashboard:", err);
    }
}

// Workout Form Submit
document.getElementById("workout-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("log-workout-btn");
    const fb = document.getElementById("workout-feedback");
    btn.disabled = true;
    fb.textContent = "Analyzing progressive overload...";
    fb.className = "feedback-msg";

    const payload = {
        exercise_name: document.getElementById("exercise-name").value,
        muscle_group: document.getElementById("muscle-group").value,
        weight_kg: parseFloat(document.getElementById("weight-kg").value),
        reps: parseInt(document.getElementById("reps").value, 10),
    };

    try {
        const res = await fetch("/api/workouts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        fb.textContent = `✓ ${data.message}`;
        fb.className = "feedback-msg feedback-success";
        await loadDashboard();
    } catch (err) {
        fb.textContent = "Failed to log workout set.";
        fb.className = "feedback-msg feedback-error";
    } finally {
        btn.disabled = false;
    }
});

// Habits Form Submit
document.getElementById("habits-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fb = document.getElementById("habits-feedback");
    fb.textContent = "Updating recovery...";

    const habitsPayload = {
        protein_grams: parseFloat(document.getElementById("protein-input").value),
        water_liters: parseFloat(document.getElementById("water-input").value),
        sleep_hours: parseFloat(document.getElementById("sleep-input").value),
    };

    const metricsPayload = {
        height_cm: parseFloat(document.getElementById("height-input").value),
        weight_kg: parseFloat(document.getElementById("weight-input").value),
    };

    try {
        await fetch("/api/habits", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(habitsPayload),
        });

        if (metricsPayload.height_cm && metricsPayload.weight_kg) {
            await fetch("/api/metrics", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(metricsPayload),
            });
        }

        fb.textContent = "✓ Fuel & body stats updated!";
        fb.className = "feedback-msg feedback-success";
        await loadDashboard();
    } catch (err) {
        fb.textContent = "Failed to update stats.";
        fb.className = "feedback-msg feedback-error";
    }
});

// AI Coach Button
document.getElementById("ask-ai-btn").addEventListener("click", async () => {
    const btn = document.getElementById("ask-ai-btn");
    const box = document.getElementById("ai-response-box");
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Analyzing Hypertrophy...';

    try {
        const res = await fetch("/api/ai-coach", { method: "POST" });
        const data = await res.json();

        box.innerHTML = `
            <div class="coach-headline">Coach Iron: "${data.coach_headline}"</div>
            <div class="coach-section">
                <div class="coach-subtitle">PROGRESSIVE OVERLOAD ANALYSIS</div>
                <p style="color: #cbd5e1">${data.overload_analysis}</p>
            </div>
            <div class="coach-section">
                <div class="coach-subtitle">RECOVERY & METRIC AUDIT</div>
                <p style="color: #cbd5e1">${data.recovery_analysis}</p>
            </div>
            <div class="coach-section">
                <div class="coach-subtitle">COACH RECOMMENDATIONS</div>
                <ul class="coach-list">
                    ${(data.recommendations || []).map(r => `<li>${r}</li>`).join("")}
                </ul>
            </div>
            <div style="margin-top: 12px; font-size: 10px; color: #64748b">
                Analysis Engine: ${data.engine || "Amazon Bedrock"} · Recommended Focus: <strong style="color: #00f0ff">${data.focus_muscle_group || "Full Body"}</strong>
            </div>
        `;
    } catch (err) {
        box.innerHTML = `<span style="color: #f43f5e">Failed to get AI Coach feedback. Check backend connection.</span>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>⚡</span> Re-Analyze With Coach Iron';
    }
});

// Initial load
loadDashboard();
