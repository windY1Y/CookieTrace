const fs = require('fs');
const path = require('path');

// 输入目录路径数组
const inputDirs = [
  '../../round3/results_non-functional_part1',
  '../../round3/results_non-functional_part2',
  '../../round3/results_non-functional_part3',
  '../../round3/results_non-functional_part4'
];

// 加载 open-cookie-database.json 文件
const cookieDatabaseFilePath = './open-cookie-database.json';
const outputFilePath = './output_cookies/output_non-functional_cookie_head.json';

// 读取并解析 cookie 数据库
const cookieDatabase = JSON.parse(fs.readFileSync(cookieDatabaseFilePath, 'utf8'));
const uniqueCookieHeads = new Set();
// 将 cookie 数据库预处理为 {cookieName: [ {vendor, category, domainOfSetCookie, description, datacontroller}, ... ]} 格式
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

// 用于存放域名及其去重后的 cookieHead 集合
const domainCookieHeads = {};

// 遍历目录和文件，收集每个域名的所有 cookieHead
inputDirs.forEach(inputDir => {
  const files = fs.readdirSync(inputDir).filter(f => f.endsWith('path.json'));
  files.forEach(file => {
    const domain = file.split('_')[0];
    const filePath = path.join(inputDir, file);
    const fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const cookieStr = fileData.cookie || '';
    // 取出 cookie 字符串的第一段（以 ';' 分隔），再取等号前的 cookie 名称作为 cookieHead
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

// 根据 cookieHead 在 cookie 数据库中查找匹配信息，并组装结果
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

// 将结果写入输出文件
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
console.log(uniqueCookieHeads, uniqueCookieHeads.size);
console.log(`Result saved to ${outputFilePath}`);

