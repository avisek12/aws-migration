{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyOutsideApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "route53:*",
        "route53domains:*",
        "cloudfront:*",
        "waf:*",
        "wafv2:*",
        "support:*",
        "trustedadvisor:*",
        "budgets:*",
        "sts:*",
        "a4b:*",
        "chime:*",
        "globalaccelerator:*",
        "importexport:*",
        "shield:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ${allowed_regions}
        }
      }
    }
  ]
}
