const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/output_non-functional_cookie_head.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/datacontroller_vendor_statistics.json'; // Path to save the output

// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Object to store the statistics for each datacontroller
const datacontrollerStats = {};

// Iterate over each domain
Object.keys(consentData).forEach(domain => {
  consentData[domain].forEach(cookie => {
    const datacontroller = cookie.datacontroller; // Extract datacontroller
    const descriptionh = cookie.descriptionh;
    const cookieHead = cookie.cookieHead;

    // Initialize the datacontroller entry if not present
    if (!datacontrollerStats[datacontroller]) {
      datacontrollerStats[datacontroller] = {
        domainCount: 0,
        domains: []
      };
    }

    // Add the domain, descriptionh, and cookieHead if the domain is not already listed
    if (!datacontrollerStats[datacontroller].domains.some(entry => entry.domain === domain)) {
      datacontrollerStats[datacontroller].domains.push({ domain, descriptionh, cookieHead });
      datacontrollerStats[datacontroller].domainCount += 1;  // Increment domain count
    }
  });
});

// Prepare the result for output
const result = Object.entries(datacontrollerStats).map(([datacontroller, data]) => ({
  datacontroller,
  domainCount: data.domainCount,
  domains: data.domains
}));
result.sort((a, b) => b.domainCount - a.domainCount);
console.log("number of datacontrollers: ", result.length);
// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
console.log(`Datacontroller statistics saved to ${outputFilePath}`);
