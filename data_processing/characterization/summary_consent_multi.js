const fs = require('fs');
const path = require('path');


const inputDirs = [
  '../round3/results_consent_part1',
  '../round3/results_consent_part2',
  '../round3/results_consent_part3',
  '../round3/results_consent_part4'
];
const outputFilePath = './consent_cookies_statistics/output_consent_multi_source.json';
const results = [];


const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}


inputDirs.forEach(inputDir => {
  try {
    
    const files = fs.readdirSync(inputDir);
    
    const jsonFiles = files.filter(file => file.endsWith('path.json'));

    console.log(`正在处理目录 ${inputDir}，共 ${jsonFiles.length} 个 path.json 文件`);

    
    jsonFiles.forEach(file => {
      const filePath = path.join(inputDir, file);
      let fileData;

      
      try {
        fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      } catch (parseErr) {
        console.error(`跳过错误文件 ${filePath}：JSON 解析失败`, parseErr.message);
        return;
      }

      
      const domain = file.split('_')[0];
      if (!domain) {
        console.warn(`跳过文件 ${file}：无法提取域名`);
        return;
      }

      
      const usedScripts = Array.isArray(fileData.used_scripts) ? fileData.used_scripts : [];
      
      const nonEmptyScripts = usedScripts.filter(script => typeof script === 'string' && script.trim() !== '');

      
      if (nonEmptyScripts.length > 1) {
        
        const domainExists = results.some(r => r.domain === domain);
        if (!domainExists) {
          const result = {
            file: file,
            domain: domain,
            used_scripts: nonEmptyScripts,
            cookie: fileData.cookie || 'No cookie data', 
            source_dir: inputDir 
          };
          results.push(result);
          console.log(`添加条目：域名 ${domain}（来自文件 ${file}）`);
        } else {
          console.log(`跳过重复域名 ${domain}（已存在于 results 中）`);
        }
      } else {
        console.log(`跳过文件 ${file}：有效脚本数量为 ${nonEmptyScripts.length}（需 >1）`);
      }
    });

  } catch (dirErr) {
    console.error(`处理目录 ${inputDir} 失败：`, dirErr.message);
  }
});


fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));


console.log(`\n=== 处理完成 ===`);
console.log(`共找到 ${results.length} 个符合条件的条目`);
console.log(`结果已保存到：${path.resolve(outputFilePath)}`);