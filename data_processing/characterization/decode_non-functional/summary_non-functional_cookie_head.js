const fs = require('fs');
const path = require('path');

const inputDirs = [
  '../../round3/results_non-functional_part1',
  '../../round3/results_non-functional_part2',
  '../../round3/results_non-functional_part3',
  '../../round3/results_non-functional_part4'
];

const cookieDatabaseFilePath = './open-cookie-database.json';
const outputFilePath = './output_cookies/output_non-functional_cookie_head.json';

const cookieDatabase = JSON.parse(fs.readFileSync(cookieDatabaseFilePath, 'utf8'));
const uniqueCookieHeads = new Set();
const cookieMap = {};
for (const vendor of Object.keys(cookieDatabase)) {
  cookieDatabase[vendor].forEach(cookie => {
    const name = cookie.cookie;
    if (!cookieMap[name]) {
      cookieMap[name] = [];
    }
    cookieMap[name].push({
      vendor,
      category: cookie.category,
      domainOfSetCookie: cookie.domain,
      description: cookie.description,
      datacontroller: cookie.dataController || 'Unknown'
    });
  });
}

const domainCookieHeads = {};

inputDirs.forEach(inputDir => {
  const files = fs.readdirSync(inputDir).filter(f => f.endsWith('path.json'));
  files.forEach(file => {
    const domain = file.split('_')[0];
    const filePath = path.join(inputDir, file);
    const fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const cookieStr = fileData.cookie || '';
    const firstPart = cookieStr.split(';')[0];
    const cookieHead = firstPart.split('=')[0].trim();
    if (!cookieHead) return;
    uniqueCookieHeads.add(cookieHead);
    if (!domainCookieHeads[domain]) {
      domainCookieHeads[domain] = new Set();
    }
    domainCookieHeads[domain].add(cookieHead);
  });
});

const result = {};
for (const domain of Object.keys(domainCookieHeads)) {
  const heads = Array.from(domainCookieHeads[domain]);
  const matches = [];
  heads.forEach(head => {
    if (cookieMap[head]) {
      cookieMap[head].forEach(info => {
        matches.push({ cookieHead: head, ...info });
      });
    }
  });
  if (matches.length > 0) {
    result[domain] = matches;
  }
}

fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
console.log(uniqueCookieHeads, uniqueCookieHeads.size);
console.log(`Result saved to ${outputFilePath}`);

