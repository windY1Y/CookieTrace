const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/output_non-functional_cookie_head.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/cookie_head_affected_websites.json'; // Path to save the output

// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Object to store the statistics for each cookieHead
const cookieHeadStats = {};

// Iterate over each domain
Object.keys(consentData).forEach(domain => {
  consentData[domain].forEach(cookie => {
    const cookieHead = cookie.cookieHead; // Extract cookieHead
    const description = cookie.description; // Extract description

    // Initialize the cookieHead entry if not present
    if (!cookieHeadStats[cookieHead]) {
      cookieHeadStats[cookieHead] = {
        domainCount: 0,
        domains: [],  // List of domains with their descriptions
        descriptions: new Set()  // Store descriptions as a set to avoid duplicates
      };
    }

    // Add the domain and description if the domain is not already listed
    if (!cookieHeadStats[cookieHead].domains.some(entry => entry.domain === domain)) {
      cookieHeadStats[cookieHead].domains.push({ domain, description });
      cookieHeadStats[cookieHead].descriptions.add(description);  // Add description to the set
      cookieHeadStats[cookieHead].domainCount += 1;  // Increment domain count
    }
  });
});

// Prepare the result for output
const result = Object.entries(cookieHeadStats).map(([cookieHead, data]) => ({
  cookieHead,
  domainCount: data.domainCount,
//   domains: data.domains,
  descriptions: Array.from(data.descriptions) // Convert descriptions set to array
}));

// Sort the result by domainCount in descending order
result.sort((a, b) => b.domainCount - a.domainCount);

// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
console.log(`CookieHead statistics saved to ${outputFilePath}`);
