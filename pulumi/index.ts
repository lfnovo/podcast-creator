import * as pulumi from "@pulumi/pulumi";
import * as cloudflare from "@pulumi/cloudflare";

const config = new pulumi.Config();
const domain = config.get('domain');
const subdomain = config.get('subdomain');
 
const bucketName = `${subdomain}`; //podcastcdn
const zoneId = "7ec73ba9e7ae3abd8134b7f8f5c1cdba";
const accountId = "2f0fa28e2eeeb947bbf466610aa69284";

const r2Bucket = new cloudflare.R2Bucket(bucketName, {
    accountId: accountId,
    name: bucketName,
    location: "weur",
    storageClass: "Standard",
});

new cloudflare.R2CustomDomain("podcast-r2-custom-domain", {
    accountId: accountId,
    bucketName: bucketName,
    domain: `${subdomain}.${domain!}`,
    enabled: true,
    zoneId,
}, {
    dependsOn: [r2Bucket],
});

// new cloudflare.Ruleset("r2-cache-rule", {
//     // zoneId: zoneId,
//     accountId: accountId,
//     kind: "zone",
//     phase: "http_request_cache_settings",
//     name: "Cache Podcasts",
//     rules: [{
//         action: "set_cache_settings",
//         expression: `(http.host eq "${bucketName}.${domain}")`,
//         description: "Cache podcasts",
//         enabled: true,
//         actionParameters: {
//             cache: true,
//             edgeTtl: {
//                 mode: "override_origin",
//                 default: 31536000,  // 1 year in seconds
//             },
//             browserTtl: {
//                 mode: "override_origin",
//                 default: 31536000,  // 1 year
//             },
//         },
//     }],
// });