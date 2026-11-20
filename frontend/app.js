const api = "http://localhost:8100";
const output = document.querySelector("#output");
const role = document.querySelector("#role");
const actor = document.querySelector("#actor");

function token() {
  return `Bearer test:${actor.value}:${role.value}`;
}

async function refresh() {
  output.textContent = "Loading…";
  try {
    const [me, health] = await Promise.all([
      fetch(`${api}/api/me`, { headers: { Authorization: token() } }).then((r) => r.json()),
      fetch(`${api}/health`).then((r) => r.json()),
    ]);
    output.textContent = JSON.stringify({ health, identity: me }, null, 2);
  } catch (error) {
    output.textContent = `Unable to reach the synthetic API: ${error}`;
  }
}

document.querySelector("#refresh").addEventListener("click", refresh);
role.addEventListener("change", () => {
  actor.value = role.value === "admin" ? "admin-1" : `${role.value}-1`;
});
