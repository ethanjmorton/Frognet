const http = require('http');
const { URL } = require('url');
const HttpProxyAgent = require('http-proxy-agent');

// URL of the Python proxy server running on Replit
const proxyUrl = "https://www.pythonanywhere.com/user/UltraWolf/shares/7cd57b362f86462cac0e3c1b67c957fa/";

// Configure the proxy agent
const agent = new HttpProxyAgent(proxyUrl);

// Example target URL (this will be proxied through the Python proxy)
const targetUrl = 'http://example.com';

const options = new URL(targetUrl);

// Attach the proxy agent to the request
options.agent = agent;

const req = http.request(options, (res) => {
    console.log(`Status: ${res.statusCode}`);

    res.setEncoding('utf8');
    res.on('data', (chunk) => {
        console.log(`Body: ${chunk}`);
    });

    res.on('end', () => {
        console.log('No more data in response.');
    });
});

req.on('error', (e) => {
    console.error(`Problem with request: ${e.message}`);
});

// End the request
req.end();
