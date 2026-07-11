/**
 * Jenkins shared library step for MISRA enterprise compliance.
 *
 * Usage in Jenkinsfile:
 *   @Library('misra-compliance') _
 *   misraCompliance(
 *     apiUrl: 'http://misra-platform:8000',
 *     runId: env.MISRA_RUN_ID,
 *     apiKey: credentials('misra-api-key')
 *   )
 */

def call(Map config) {
    def apiUrl = config.apiUrl
    def runId = config.runId
    def apiKey = config.apiKey ?: ''
    def teamId = config.teamId ?: ''

    stage('MISRA SARIF Export') {
        sh """
            curl -fsS \\
              -H 'X-API-Key: ${apiKey}' \\
              '${apiUrl}/api/v1/analysis/runs/${runId}/export/sarif' \\
              -o misra-results.sarif.json
        """
        archiveArtifacts artifacts: 'misra-results.sarif.json', fingerprint: true
    }

    stage('MISRA GitHub-style Annotations') {
        sh """
            curl -fsS \\
              -H 'X-API-Key: ${apiKey}' \\
              '${apiUrl}/api/v1/analysis/runs/${runId}/export/github-annotations' \\
              -o annotations.json
        """
        archiveArtifacts artifacts: 'annotations.json'
    }

    stage('MISRA PR Comment') {
        sh """
            curl -fsS -X POST \\
              -H 'Content-Type: application/json' \\
              -H 'X-API-Key: ${apiKey}' \\
              -d '{"platform":"github"}' \\
              '${apiUrl}/api/v1/analysis/runs/${runId}/integrations/pr-comment' \\
              -o pr-comment.json
        """
    }

    stage('MISRA Compliance Snapshot') {
        def body = teamId ? "{\\"team_id\\":\\"${teamId}\\"}" : '{}'
        sh """
            curl -fsS -X POST \\
              -H 'Content-Type: application/json' \\
              -H 'X-API-Key: ${apiKey}' \\
              -d '${body}' \\
              '${apiUrl}/api/v1/analysis/runs/${runId}/compliance-snapshot'
        """
    }

    if (teamId) {
        stage('MISRA Round-Robin Reviewer Assignment') {
            sh """
                curl -fsS -X POST \\
                  -H 'Content-Type: application/json' \\
                  -H 'X-API-Key: ${apiKey}' \\
                  -d '{"run_id":"${runId}","team_id":"${teamId}","actor_id":"jenkins"}' \\
                  '${apiUrl}/api/v1/integrations/round-robin-assign'
            """
        }
    }
}

return this
