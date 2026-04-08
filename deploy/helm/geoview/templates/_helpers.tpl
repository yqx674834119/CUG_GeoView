{{- define "geoview.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "geoview.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "geoview.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "geoview.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "geoview.labels" -}}
helm.sh/chart: {{ include "geoview.chart" . }}
app.kubernetes.io/name: {{ include "geoview.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "geoview.selectorLabels" -}}
app.kubernetes.io/name: {{ include "geoview.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "geoview.appName" -}}
{{- printf "%s-app" (include "geoview.fullname" .) -}}
{{- end -}}

{{- define "geoview.mysqlName" -}}
{{- printf "%s-mysql" (include "geoview.fullname" .) -}}
{{- end -}}

{{- define "geoview.mysqlHost" -}}
{{- if .Values.mysql.enabled -}}
{{ include "geoview.mysqlName" . }}
{{- else -}}
{{ required "externalMySQL.host is required when mysql.enabled=false" .Values.externalMySQL.host }}
{{- end -}}
{{- end -}}

