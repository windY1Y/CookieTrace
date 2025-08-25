const fs = require('fs');
const path = require('path');
const { diff } = require('util');


const inputDirs = [
    '../round3/results_non-functional_part1',
    '../round3/results_non-functional_part2',
    '../round3/results_non-functional_part3',
    '../round3/results_non-functional_part4'
];
const outputFilePath = './non-functional_cookies_statistics/tiktok_stack_and_source_diff.json'; 


const scriptStats = Object.create(null);
diffList = [];

inputDirs.forEach(dir => {
    const dirPath = path.resolve(__dirname, dir);
    if (!fs.existsSync(dirPath)) {
        console.warn(`Warning: directory ${dirPath} does not exist, skipping.`);
        return;
    }

    const entries = fs.readdirSync(dirPath);
    entries.forEach(file => {
        if (!file.endsWith('path.json')) {
            return;
        }
        const filePath = path.join(dirPath, file);
        let fileData;
        try {
            fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        } catch (err) {
            console.error(`Failed to parse JSON from ${filePath}:`, err);
            return;
        }

        
        const domain = file.split('_')[0];

        
        const stackTrace = Array.isArray(fileData.stack_trace)
            ? fileData.stack_trace.filter(s => s && typeof s === 'string' && s.trim() !== '')
            : [];

        let stackNotIncludetTiktok = true;
        let sourceNotIncludetTiktok = true;
        
        console.log(`dealing: ${file} from ${dir}`);
        stackTrace.forEach(script => {
            let scriptPrefix = script.split('?')[0]; 
            const lastSlashIndex = script.lastIndexOf('/');
            const scriptName = script.substring(lastSlashIndex + 1); 
            const scriptfiledir = script.substring(0, script.lastIndexOf('/'));
            if ((scriptName.match(/\./g) || []).length >= 1) {
                scriptPrefix = script.substring(0, scriptfiledir.length + scriptName.indexOf('.') + 1);
            }
            if(script.includes('https://analytics.tiktok.com/')){
                console.log(`Stack trace includes TikTok script: ${script}`);
                stackNotIncludetTiktok = false;
                return;
            }
        });

        const usedScripts = Array.isArray(fileData.used_scripts)
            ? fileData.used_scripts.filter(s => s && typeof s === 'string' && s.trim() !== '')
            : [];
        usedScripts.forEach(script => {
            let scriptPrefix = script.split('?')[0]; 
            const lastSlashIndex = script.lastIndexOf('/');
            const scriptName = script.substring(lastSlashIndex + 1); 
            const scriptfiledir = script.substring(0, script.lastIndexOf('/'));
            if ((scriptName.match(/\./g) || []).length >= 1) {
                scriptPrefix = script.substring(0, scriptfiledir.length + scriptName.indexOf('.') + 1);
            }
            if(script.includes('https://analytics.tiktok.com/')){
                console.log(`Used scripts includes TikTok script: ${script}`);
                sourceNotIncludetTiktok = false;
                return;
            }
        });
        if(stackNotIncludetTiktok && !sourceNotIncludetTiktok) {
            diffList.push({
                file: file,
                domain: domain,
                cookie: fileData.cookie,
                stack_trace: stackTrace,
                used_scripts: usedScripts
            });
        }
    });
});



try {
    fs.writeFileSync(outputFilePath, JSON.stringify(diffList, null, 2));
    console.log(`Diff results saved to ${outputFilePath}`);
} catch (err) {
    console.error(`Failed to write output file ${outputFilePath}:`, err);
}
