async function getJSON(url, opts = {}) {
  const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opts });
  return res.json();
}

function setBalanceUI(data) {
  const bal = data.balance;
  const need = data.need;
  document.getElementById("balanceText").textContent = `${bal} min`;
  document.getElementById("needText").textContent = `To break even: ${need} min`;
  document.getElementById("targetText").textContent = data.target;
  document.getElementById("todayText").textContent = data.today;

  const card = document.getElementById("balanceCard");
  card.style.border = bal >= 0 ? "1px solid rgba(55,214,122,0.4)" : "1px solid rgba(255,92,92,0.4)";
}

async function refresh() {
  const data = await getJSON("/api/state");
  setBalanceUI(data);
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return res.json();
}

window.addEventListener("DOMContentLoaded", () => {
  refresh();

  document.getElementById("workBtn").addEventListener("click", async () => {
    const v = parseInt(document.getElementById("workInput").value, 10);
    if (isNaN(v) || v <= 0) return alert("Enter minutes (e.g. 45)");
    await postJSON("/api/work", { minutes: v });
    document.getElementById("workInput").value = "";
    refresh();
  });

  document.getElementById("relaxBtn").addEventListener("click", async () => {
    const v = parseInt(document.getElementById("relaxInput").value, 10);
    if (isNaN(v) || v <= 0) return alert("Enter minutes (e.g. 30)");
    await postJSON("/api/relax", { minutes: v });
    document.getElementById("relaxInput").value = "";
    refresh();
  });

  document.getElementById("targetBtn").addEventListener("click", async () => {
    const v = parseInt(document.getElementById("targetInput").value, 10);
    if (isNaN(v) || v <= 0) return alert("Enter target minutes (e.g. 120)");
    await postJSON("/api/target", { target: v });
    document.getElementById("targetInput").value = "";
    refresh();
  });
});
