const fs = require("fs");
const https = require("https");

const username = "muhamadrenald"; // GANTI jika perlu

function fetchRepos() {
  return new Promise((resolve) => {
    https.get(`https://api.github.com/users/${username}/repos`, {
      headers: { "User-Agent": "node" }
    }, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => resolve(JSON.parse(data)));
    });
  });
}

async function main() {
  const repos = await fetchRepos();

  let langCount = {};

  repos.forEach(repo => {
    if (repo.language) {
      langCount[repo.language] = (langCount[repo.language] || 0) + 1;
    }
  });

  const total = Object.values(langCount).reduce((a, b) => a + b, 0);

  let result = "## 🎯 Skills & Expertise (Auto Updated)\n\n";
  result += "| Language | Usage |\n|---|---|\n";

  Object.entries(langCount)
    .sort((a, b) => b[1] - a[1])
    .forEach(([lang, count]) => {
      const percent = ((count / total) * 100).toFixed(0);
      const bar = "█".repeat(Math.floor(percent / 5));
      result += `| ${lang} | ${bar} ${percent}% |\n`;
    });

  let readme = fs.readFileSync("README.md", "utf-8");

  const start = "<!--START_SECTION:skills-->";
  const end = "<!--END_SECTION:skills-->";

  const newContent = `${start}\n${result}\n${end}`;

  const regex = new RegExp(`${start}[\\s\\S]*${end}`);

  readme = readme.replace(regex, newContent);

  fs.writeFileSync("README.md", readme);
}

main();
