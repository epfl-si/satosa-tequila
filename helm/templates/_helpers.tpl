{{/*
Expand the name of the chart.
*/}}
{{- define "satosa-tequila.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "satosa-tequila.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "satosa-tequila.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "satosa-tequila.labels" -}}
helm.sh/chart: {{ include "satosa-tequila.chart" . }}
{{ include "satosa-tequila.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "satosa-tequila.selectorLabels" -}}
app.kubernetes.io/name: {{ include "satosa-tequila.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "satosa-tequila.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "satosa-tequila.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Whether OpenShift-style “cloud build” is available
*/}}
{{- define "hasOpenShiftBuilds" -}}
{{- if and (.Capabilities.APIVersions.Has "image.openshift.io/v1")
           (.Capabilities.APIVersions.Has "build.openshift.io/v1") -}}
true
{{- else -}}
false
{{- end }}
{{- end }}

{{/*
Whether the target cluster uses the Quay bridge operator
*/}}
{{- define "hasQuayBridge" -}}
{{- if (gt 0 (len lookup "quay.redhat.com/v1" "QuayIntegration")) -}}
true
{{- else -}}
false
{{- end }}
{{- end }}
