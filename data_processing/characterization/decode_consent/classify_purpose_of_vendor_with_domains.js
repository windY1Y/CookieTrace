const fs = require('fs');
const path = require('path');

// 1. 配置文件路径（修改为：读取detail_vendor_positive_description_purpose.json，输出purpose_positive_with_domains.json）
const inputFilePath = './output_cookies/detail_vendor_positive_description_purpose.json'; // 输入：已整合的供应商-目的-域名数据
const outputFilePath = './output_cookies/purpose_positive_with_domains.json'; // 输出：Purpose-ID对应的域名统计结果

// 2. 工具函数：读取JSON文件（复用原脚本的错误处理逻辑，确保可靠性）
function readJsonFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      throw new Error(`文件不存在`);
    }
    const fileContent = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(fileContent);
  } catch (err) {
    console.error(`读取文件 ${filePath} 失败：`, err.message);
    process.exit(1);
  }
}

// 3. 核心逻辑：按Purpose ID统计域名（去重+关联目的信息）
function PurposeStatic(vendorPurposeData) {
  // 存储结果映射：key=Purpose ID（字符串，避免数字/字符串ID差异），value=目的详情+去重域名列表
  const purposeDomainMap = {};

  // 遍历每个供应商的完整信息（从输入文件中读取的每条数据）
  vendorPurposeData.forEach(vendorItem => {
    const currentVendorDomains = vendorItem.domains || []; // 当前供应商影响的域名列表
    const currentVendorPurposes = vendorItem.vendorPurposesDetail?.purposes || []; // 当前供应商关联的所有Purpose

    // 遍历当前供应商的每个Purpose，将域名关联到对应Purpose
    currentVendorPurposes.forEach(purpose => {
      // 统一Purpose ID为字符串（避免1和"1"被识别为不同ID）
      const purposeIdStr = String(purpose.purposeId);
      // 提取当前Purpose的基础信息（名称、描述，确保统计结果有上下文）
      const purposeName = purpose.purposeName || 'Unknown Purpose Name';
      const purposeDescription = purpose.purposeDescription || 'No Description Available';

      // 初始化：若该Purpose ID未在映射中，创建基础结构（用Set存储域名实现自动去重）
      if (!purposeDomainMap[purposeIdStr]) {
        purposeDomainMap[purposeIdStr] = {
          purposeId: purpose.purposeId, // 保留原始数字ID（便于后续排序/匹配）
          purposeName: purposeName,
          purposeDescription: purposeDescription,
          domains: new Set() // Set特性：自动过滤重复域名，比数组includes()效率更高
        };
      }

      // 将当前供应商的域名添加到该Purpose的Set中（自动去重）
      currentVendorDomains.forEach(domain => {
        purposeDomainMap[purposeIdStr].domains.add(domain);
      });
    });
  });

  // 格式转换：将Set转为数组（JSON不支持Set序列化），并补充域名数量
  let finalResult = Object.values(purposeDomainMap).map(purposeItem => ({
    purposeId: purposeItem.purposeId,
    purposeName: purposeItem.purposeName,
    purposeDescription: purposeItem.purposeDescription,
    domainCount: purposeItem.domains.size, // 去重后的域名总数
    domains: Array.from(purposeItem.domains).sort() // 转为数组并按字母排序（便于阅读）
  }));

  // 核心修改：按【域名个数（domainCount）降序排序】（优先级高于ID排序，符合需求）
  finalResult.sort((a, b) => {
    // 第一排序维度：domainCount降序（域名多的排在前面）
    if (b.domainCount !== a.domainCount) {
      return b.domainCount - a.domainCount;
    }
    // 第二排序维度：purposeId升序（域名数相同时，按ID从小到大排序，避免结果混乱）
    return a.purposeId - b.purposeId;
  });

  return finalResult;
}

// 4. 确保输出目录存在（复用原脚本逻辑，避免写入失败）
const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`提示：自动创建输出目录 ${outputDir}`);
}

// 5. 主流程：读取数据→统计→写入结果
try {
  // 步骤1：读取输入文件（detail_vendor_positive_description_purpose.json）
  const vendorPurposeData = readJsonFile(inputFilePath);
  console.log(`✅ 成功读取输入文件，共包含 ${vendorPurposeData.length} 个供应商的信息`);

  // 步骤2：执行统计逻辑
  const purposeDomainResult = PurposeStatic(vendorPurposeData);
  console.log(`📊 统计完成，共涉及 ${purposeDomainResult.length} 个不同的Purpose ID`);

  // 步骤3：写入输出文件
  fs.writeFileSync(outputFilePath, JSON.stringify(purposeDomainResult, null, 2));
  console.log(`✅ 统计结果已保存到：${path.resolve(outputFilePath)}`);

  // 步骤4：补充统计汇总（增强用户体验，快速了解数据概况）
  const totalUniqueDomains = purposeDomainResult.reduce((sum, item) => sum + item.domainCount, 0);
  const avgDomainsPerPurpose = purposeDomainResult.length > 0 
    ? (totalUniqueDomains / purposeDomainResult.length).toFixed(2) 
    : "0.00";
  console.log(`\n📈 统计汇总：`);
  console.log(`   - 总Purpose ID数量：${purposeDomainResult.length}`);
  console.log(`   - 所有Purpose覆盖的去重后域名总数：${totalUniqueDomains}`);
  console.log(`   - 平均每个Purpose覆盖的域名数：${avgDomainsPerPurpose}`);

  // 打印Top3覆盖域名最多的Purpose（因结果已按domainCount降序，直接取前3即可）
  const top3Purpose = purposeDomainResult.slice(0, 3);
  console.log(`\n🏆 覆盖域名最多的3个Purpose：`);
  top3Purpose.forEach((item, index) => {
    console.log(`   ${index + 1}. Purpose ${item.purposeId}（${item.purposeName}）：${item.domainCount} 个域名`);
  });

} catch (err) {
  console.error(`❌ 执行失败：`, err.message);
  process.exit(1);
}