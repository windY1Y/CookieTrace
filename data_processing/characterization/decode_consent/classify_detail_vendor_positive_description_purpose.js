const fs = require('fs');
const path = require('path');

// 1. 配置文件路径（相对路径，可根据实际目录结构调整）
const vendorPositiveStatsPath = './output_cookies/vendors_positive_statistics_all_consent.json';
const vendorListPath = './vendor-list.json';
const outputFilePath = './output_cookies/detail_vendor_positive_description_purpose.json';

// 2. 工具函数：读取JSON文件（封装错误处理，确保关键文件读取失败时终止并提示）
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

// 3. 读取核心文件内容
const vendorPositiveStats = readJsonFile(vendorPositiveStatsPath); // 供应商-域名统计数据
const vendorList = readJsonFile(vendorListPath); // 包含purposes和vendors的完整GVL列表

// 4. 构建关键映射表（提升匹配效率）
// 4.1 供应商ID -> 供应商详细信息映射
const vendorIdToDetailMap = {};
for (const vendorId in vendorList.vendors) {
  vendorIdToDetailMap[vendorId] = vendorList.vendors[vendorId];
}

// 4.2 目的ID -> 目的详细信息映射（从vendor-list.json的purposes字段提取）
const purposeIdToDetailMap = {};
for (const purposeId in vendorList.purposes) {
  purposeIdToDetailMap[purposeId] = vendorList.purposes[purposeId];
}

// 5. 核心逻辑：整合供应商-域名数据 + 供应商目的ID + 目的详细信息
const result = vendorPositiveStats.map(positiveItem => {
  const vendorId = positiveItem.vendorPositiveId;
  const vendorDetail = vendorIdToDetailMap[vendorId] || null;
  const vendorPurposes = vendorDetail ? vendorDetail.purposes || [] : []; // 供应商关联的目的ID列表

  // 关键步骤：为每个目的ID匹配对应的详细信息（name、description等）
  const matchedPurposes = vendorPurposes.map(purposeId => {
    const purposeDetail = purposeIdToDetailMap[String(purposeId)] || null; // 目的ID可能是数字，转为字符串匹配映射表
    return purposeDetail
      ? {
          purposeId: purposeDetail.id,
          purposeName: purposeDetail.name,
          purposeDescription: purposeDetail.description,
          purposeIllustrations: purposeDetail.illustrations || [] // 目的说明案例（可选保留）
        }
      : {
          purposeId: purposeId,
          status: "Unknown Purpose",
          message: `在 vendor-list.json 的 purposes 中未找到ID为 ${purposeId} 的目的信息`
        };
  });

  // 整合最终结果
  return {
    // 保留 vendors_positive_statistics_all_consent.json 中的核心字段（域名相关）
    vendorPositiveId: vendorId,
    vendorName: positiveItem.vendorName,
    domainCount: positiveItem.domainCount,
    domains: positiveItem.domains,

    // 补充供应商基础信息（来自 vendor-list.json 的 vendors 字段）
    vendorBasicInfo: vendorDetail
      ? {
          gvlId: vendorDetail.id,
          fullName: vendorDetail.name,
          usesCookies: vendorDetail.usesCookies,
          cookieMaxAgeSeconds: vendorDetail.cookieMaxAgeSeconds
        }
      : {
          status: "Unknown Vendor",
          message: `在 vendor-list.json 的 vendors 中未找到ID为 ${vendorId} 的供应商信息`
        },

    // 核心新增：供应商关联的目的ID及对应的详细信息（匹配 vendor-list.json 的 purposes 字段）
    vendorPurposesDetail: {
      totalPurposeCount: matchedPurposes.length, // 供应商关联的目的总数
      purposes: matchedPurposes // 每个目的的详细信息列表
    }
  };
});

// 6. 确保输出目录存在（避免写入失败）
const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`提示：自动创建输出目录 ${outputDir}`);
}

// 7. 写入输出文件并打印统计信息
try {
  fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
  
  // 统计有效匹配数据（便于快速了解结果完整性）
  const validVendorCount = result.filter(item => item.vendorBasicInfo.status !== "Unknown Vendor").length;
  const totalVendorCount = result.length;
  const avgPurposePerVendor = totalVendorCount > 0 
    ? (result.reduce((sum, item) => sum + item.vendorPurposesDetail.totalPurposeCount, 0) / totalVendorCount).toFixed(2)
    : "0.00";

  console.log(`✅ 结果已保存到：${path.resolve(outputFilePath)}`);
  console.log(`📊 统计汇总：`);
  console.log(`   - 总供应商数量：${totalVendorCount}`);
} catch (err) {
  console.error(`❌ 写入输出文件失败：`, err.message);
  process.exit(1);
}