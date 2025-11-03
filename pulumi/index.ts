import * as pulumi from "@pulumi/pulumi";
import * as cloudflare from "@pulumi/cloudflare";

const config = new pulumi.Config();
const bucketName = "podcast-bucket";
const zoneId = "ff78d7733bafe5ec08240fd2dcf39e3c";
const accountId = "2f0fa28e2eeeb947bbf466610aa69284";
const domain = config.get('domain');

new cloudflare.R2Bucket(bucketName, {
    accountId: accountId,
    name: bucketName,
    location: "weur",
    storageClass: "Standard",
});

new cloudflare.R2CustomDomain("podcast-r2-custom-domain", {
    accountId: accountId,
    bucketName: bucketName,
    domain: `${bucketName}.${domain!}`,
    enabled: true,
    zoneId,
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