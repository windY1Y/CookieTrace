const fs = require('fs');
const path = require('path'); // 用于处理输出目录路径

// 配置文件路径
const inputFilePath = './output_cookies/decode_output_consent.json'; // 输入JSON文件路径
const outputFilePath = './output_cookies/multi_legit_all_consent.json'; // 输出文件路径

// 读取输入JSON数据
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// 用Set存储符合条件的域名（自动去重，无需手动判断重复）
const qualifiedDomains = new Set();

// 遍历所有数据项，筛选符合条件的域名
consentData.forEach(item => {
  // 1. 从文件名提取域名（第一个下划线之前的部分）
  const domain = item.file.split('_')[0];
  if (!domain) {
    console.warn(`Warning: 无法从文件 "${item.file}" 提取域名，跳过该条目`);
    return;
  }

  // 2. 获取vendorLegitSize和purposeLegitSize（默认0，避免undefined导致判断错误）
  const vendorLegitSize = item.vendorLegitSize || 0;
  const purposeLegitSize = item.purposeLegitSize || 0;

  // 3. 筛选条件：vendorLegitSize>1 或 purposeLegitSize>1，符合则加入Set
  if (vendorLegitSize > 1 || purposeLegitSize > 1) {
    qualifiedDomains.add(domain);
  }
});

// 4. 整理输出结果（仅包含总数和去重后的域名列表）
const result = {
  totalQualifiedDomainCount: qualifiedDomains.size, // 符合条件的域名总数
  qualifiedDomainList: Array.from(qualifiedDomains) // 去重后的域名列表（Set转数组便于JSON序列化）
};

// 5. 确保输出目录存在（避免因目录不存在导致写入失败）
const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Info: 自动创建输出目录 "${outputDir}"`);
}

// 6. 将结果写入输出文件（格式化JSON，缩进2空格，便于阅读）
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

// 7. 控制台输出统计结果，便于快速查看
console.log('=== 域名筛选统计完成 ===');
console.log(`符合条件的域名总数：${qualifiedDomains.size}`);
console.log(`去重后的域名列表已保存到：${path.resolve(outputFilePath)}`);