#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

CHART_DIR="${SCRIPT_DIR}/deploy/helm/geoview"
DIST_DIR="${SCRIPT_DIR}/deploy/helm/dist"
DOC_DIR="${SCRIPT_DIR}/docs"

mkdir -p "${DIST_DIR}"

CHART_VERSION="$(sed -n 's/^version: //p' "${CHART_DIR}/Chart.yaml" | head -n 1 | tr -d '\"')"
if [ -z "${CHART_VERSION}" ]; then
  echo "Failed to read chart version from ${CHART_DIR}/Chart.yaml"
  exit 1
fi

CHART_PACKAGE="${DIST_DIR}/geoview-${CHART_VERSION}.tgz"
THIN_BUNDLE="${DIST_DIR}/GeoView_Helm_Thin_$(date +%Y%m%d).tar.gz"

rm -f "${CHART_PACKAGE}" "${THIN_BUNDLE}"

tar -czf "${CHART_PACKAGE}" -C "${SCRIPT_DIR}/deploy/helm" geoview

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${TMP_DIR}/GeoView_Helm_Thin"
cp "${CHART_PACKAGE}" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${DOC_DIR}/Helm_K8s_部署入门与迁移说明.md" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${DOC_DIR}/Helm_两步交付与平台部署说明.md" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${DOC_DIR}/GeoView_Helm_最终交付手册.md" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${CHART_DIR}/values-harbor-example.yaml" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${SCRIPT_DIR}/deploy/helm/image-manifest.txt" "${TMP_DIR}/GeoView_Helm_Thin/"
cp "${SCRIPT_DIR}/deploy/helm/push_harbor_with_nerdctl_example.sh" "${TMP_DIR}/GeoView_Helm_Thin/"

tar -czf "${THIN_BUNDLE}" -C "${TMP_DIR}" GeoView_Helm_Thin

echo "=========================================="
echo "Helm chart package: ${CHART_PACKAGE}"
echo "Lightweight handoff bundle: ${THIN_BUNDLE}"
echo "=========================================="
