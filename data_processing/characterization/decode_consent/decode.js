const fs = require('fs');
const path = require('path');
const { TCString, TCModel } = require('@iabtcf/core');

const inputDirs = ['../../round3/results_consent_part1', '../../round3/results_consent_part2', '../../round3/results_consent_part3', '../../round3/results_consent_part4'];  // 目录数组
const outputFilePath = './output_cookies/decode_output_consent.json';  // 输出结果文件路径

// 用于存放所有解码结果
const decodedResults = [];
const seenDomains = new Set();  // 用于存储已经处理的域名
var fault_cnt = 0;

// 遍历多个目录
inputDirs.forEach(inputDir => {
  // 读取目录下所有 path.json 文件
  fs.readdir(inputDir, (err, files) => {
    if (err) {
      console.error(`读取目录 ${inputDir} 失败:`, err);
      return;
    }

    // 筛选出所有 path.json 文件
    const jsonFiles = files.filter(file => file.endsWith('path.json'));

    // 遍历每个文件进行解码
    jsonFiles.forEach((file) => {
      const filePath = path.join(inputDir, file);
      const fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      // 获取 cookie 编码字段并解码
      const cookieEncoded = fileData.cookie.split('=')[1].split(';')[0];
      console.log(`正在解码文件: ${file} 来自 ${inputDir}`);
      console.log(`Cookie 编码: ${cookieEncoded}`);

      // 提取域名（文件名中的第一个下划线之前部分）
      const domain = file.split('_')[0];

      // 如果该域名已经处理过，则跳过
      if (seenDomains.has(domain)) {
        console.log(`跳过域名 ${domain}，该域名的文件已处理`);
        return;
      }
      seenDomains.add(domain);  // 标记该域名为已处理

      if (cookieEncoded) {
        try {
          const myTCModel = TCString.decode(cookieEncoded);

          // 获取供应商同意、目的同意、供应商合法利益等
          const vendorConsents = Array.from(myTCModel.vendorConsents || []);
          const purposeConsents = Array.from(myTCModel.purposeConsents || []);
          const vendorLegit = Array.from(myTCModel.vendorLegitimateInterests || []);
          const purposeLegit = Array.from(myTCModel.purposeLegitimateInterests || []);
          const specialFeatures = Array.from(myTCModel.specialFeatureOptins || []);

          // 过滤出只包含值为 true 的项，直接保留 id
          const vendorConsentDetails = vendorConsents.filter(([id, value]) => value === true).map(([id]) => id);
          const purposeConsentDetails = purposeConsents.filter(([id, value]) => value === true).map(([id]) => id);
          const vendorLegitDetails = vendorLegit.filter(([id, value]) => value === true).map(([id]) => id);
          const purposeLegitDetails = purposeLegit.filter(([id, value]) => value === true).map(([id]) => id);
          const specialFeatureDetails = specialFeatures.filter(([id, value]) => value === true).map(([id]) => id);

          // 获取各项的 size
          const vendorConsentsSize = vendorConsents.filter(([id, value]) => value === true).length;
          const purposeConsentsSize = purposeConsents.filter(([id, value]) => value === true).length;
          const vendorLegitSize = vendorLegit.filter(([id, value]) => value === true).length;
          const purposeLegitSize = purposeLegit.filter(([id, value]) => value === true).length;
          const specialFeatureSize = specialFeatures.filter(([id, value]) => value === true).length;

          // 将结果添加到数组中
          decodedResults.push({
            file: file,  // 文件名
            cookie: fileData.cookie,
            vendorConsentsSize,
            vendorConsentDetails,
            purposeConsentsSize,
            purposeConsentDetails,
            vendorLegitSize,
            vendorLegitDetails,
            purposeLegitSize,
            purposeLegitDetails,
            specialFeatureSize,
            specialFeatureDetails,
            cmpId: myTCModel.cmpId
          });
          console.log(`解码完成，${file} 结果已保存到 decodedResults`);
        } catch (e) {
          console.error('解码失败:', e);
          fault_cnt++;
          console.log('-1 -1 -1 -1 -1 -1');
        }
      }
    });

    // 将结果写入到文件
    if (decodedResults.length > 0) {
      fs.writeFileSync(outputFilePath, JSON.stringify(decodedResults, null, 2));
      console.log(`解码完成，所有结果已保存到 ${outputFilePath}`);
    }

    if(fault_cnt > 0) {
      console.log(`解码失败的文件数: ${fault_cnt}`);
    }
  });
});
