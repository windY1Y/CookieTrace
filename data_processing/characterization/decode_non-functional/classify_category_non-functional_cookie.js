const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/output_non-functional_cookie_head.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/category_affected_websites.json'; // Path to save the output

// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Object to store the statistics for each category
const categoryStats = {};

// Iterate over each domain
Object.keys(consentData).forEach(domain => {
  consentData[domain].forEach(cookie => {
    const category = cookie.category; // Extract category (instead of description)
    const cookieHead = cookie.cookieHead;

    // Initialize the category entry if not present
    if (!categoryStats[category]) {
      categoryStats[category] = {
        domainCount: 0,
        domains: []
      };
    }

    // Add the domain and cookieHead if the domain is not already listed
    if (!categoryStats[category].domains.some(entry => entry.domain === domain)) {
      categoryStats[category].domains.push({ domain, cookieHead });
      categoryStats[category].domainCount += 1;  // Increment domain count
    }
  });
});

// Prepare the result for output
const result = Object.entries(categoryStats).map(([category, data]) => ({
  category,
  domainCount: data.domainCount,
  domains: data.domains
}));

// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
console.log(`Category statistics saved to ${outputFilePath}`);
