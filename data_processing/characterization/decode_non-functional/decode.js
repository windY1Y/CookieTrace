const fs = require('fs');
const path = require('path');
const { TCString, TCModel } = require('@iabtcf/core');

const inputDirs = ['../../round3/results_non-functional_part1', '../../round3/results_non-functional_part2', '../../round3/results_non-functional_part3', '../../round3/results_non-functional_part4'];
const outputFilePath = './output_cookies/decode_output_non-functional.json';

const decodedResults = [];
const seenDomains = new Set();
var fault_cnt = 0;

inputDirs.forEach(inputDir => {
  fs.readdir(inputDir, (err, files) => {
    if (err) {
      console.error(`Failed to read directory ${inputDir}:`, err);
      return;
    }

    const jsonFiles = files.filter(file => file.endsWith('path.json'));

    jsonFiles.forEach((file) => {
      const filePath = path.join(inputDir, file);
      const fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      const cookieEncoded = fileData.cookie.split('=')[1].split(';')[0];
      console.log(`Decoding file ${file} from ${inputDir}`);
      console.log(`Encoded cookie: ${cookieEncoded}`);

      const domain = file.split('_')[0];

      if (seenDomains.has(domain)) {
        console.log(`Skipping domain ${domain}: already processed`);
        return;
      }
      seenDomains.add(domain);

      if (cookieEncoded) {
        try {
          const myTCModel = TCString.decode(cookieEncoded);

          const vendorConsents = Array.from(myTCModel.vendorConsents || []);
          const purposeConsents = Array.from(myTCModel.purposeConsents || []);
          const vendorLegit = Array.from(myTCModel.vendorLegitimateInterests || []);
          const purposeLegit = Array.from(myTCModel.purposeLegitimateInterests || []);
          const specialFeatures = Array.from(myTCModel.specialFeatureOptins || []);

          const vendorConsentDetails = vendorConsents.filter(([id, value]) => value === true).map(([id]) => id);
          const purposeConsentDetails = purposeConsents.filter(([id, value]) => value === true).map(([id]) => id);
          const vendorLegitDetails = vendorLegit.filter(([id, value]) => value === true).map(([id]) => id);
          const purposeLegitDetails = purposeLegit.filter(([id, value]) => value === true).map(([id]) => id);
          const specialFeatureDetails = specialFeatures.filter(([id, value]) => value === true).map(([id]) => id);

          decodedResults.push({
            file: file,
            cookie: fileData.cookie,
            vendorConsentsSize: vendorConsents.filter(([id, value]) => value === true).length,
            vendorConsentDetails,
            purposeConsentsSize: purposeConsents.filter(([id, value]) => value === true).length,
            purposeConsentDetails,
            vendorLegitSize: vendorLegit.filter(([id, value]) => value === true).length,
            vendorLegitDetails,
            purposeLegitSize: purposeLegit.filter(([id, value]) => value === true).length,
            purposeLegitDetails,
            specialFeatureSize: specialFeatures.filter(([id, value]) => value === true).length,
            specialFeatureDetails,
            cmpId: myTCModel.cmpId
          });
          console.log(`Decoded ${file}; stored output in decodedResults`);
        } catch (e) {
          console.error('Decoding failed:', e);
          fault_cnt++;
          console.log('-1 -1 -1 -1 -1 -1');
        }
      }
    });

    if (decodedResults.length > 0) {
      fs.writeFileSync(outputFilePath, JSON.stringify(decodedResults, null, 2));
      console.log(`Decoding complete; results saved to ${outputFilePath}`);
    }

    if(fault_cnt > 0) {
      console.log(`Files that failed decoding: ${fault_cnt}`);
    }
  });
});
