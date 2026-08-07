---
name: k8s-rollback
description: Use this skill when a Kubernetes deployment is failing and needs to be rolled back or stabilized — crash-looping pods, a bad image tag, failed readiness probes, or a rollout stuck partway. Triggers include 'rollback the deploy', 'pods are crashlooping', 'rollout stuck'.
license: Apache-2.0
allowed-tools: [Bash, Read]
---

# Deployment rollback

## Instructions

1. Capture the current rollout history and the failing pod logs before changing anything
2. Confirm the previous revision is actually healthy rather than merely older
3. Roll back to that revision and watch readiness rather than pod status
4. Only then investigate the root cause of the bad revision

## Success criteria

- Logs from the failing revision are captured before rollback
- Readiness, not pod phase, is used to declare recovery
- The bad image tag is recorded for the follow-up investigation
