{{- define "lchai.image" -}}
{{ .Values.image.registry }}/{{ .Values.image.prefix }}/{{ .svc }}:{{ .Values.image.tag }}
{{- end -}}

{{- define "lchai.envFrom" -}}
- configMapRef:
    name: lchai-config
- secretRef:
    name: lchai-secrets
{{- end -}}
