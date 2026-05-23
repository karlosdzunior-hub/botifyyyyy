const RAILWAY_API = 'https://backboard.railway.app/graphql/v2'

interface RailwayConfig {
  apiToken: string
  projectId: string
}

interface DeployResult {
  serviceId: string
  dashboardUrl: string
}

async function gql(token: string, query: string, variables: Record<string, unknown>) {
  const res = await fetch(RAILWAY_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query, variables }),
  })
  const json = (await res.json()) as { data?: Record<string, unknown>; errors?: { message: string }[] }
  if (json.errors?.length) throw new Error(json.errors[0].message)
  return json.data!
}

async function createService(token: string, projectId: string, name: string): Promise<string> {
  const data = await gql(token, `
    mutation serviceCreate($input: ServiceCreateInput!) {
      serviceCreate(input: $input) { id }
    }
  `, { input: { projectId, name } })
  return (data.serviceCreate as { id: string }).id
}

async function setEnvVar(token: string, projectId: string, serviceId: string, name: string, value: string) {
  await gql(token, `
    mutation variableUpsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
  `, { input: { projectId, serviceId, name, value } })
}

async function deployCode(token: string, serviceId: string, code: string) {
  const requirements = 'python-telegram-bot==20.7\nhttpx==0.27.0\n'
  const procfile     = 'web: python main.py\n'

  const toB64 = (s: string) => Buffer.from(s).toString('base64')

  await gql(token, `
    mutation serviceSourceDeploy($input: ServiceSourceDeployInput!) {
      serviceSourceDeploy(input: $input)
    }
  `, {
    input: {
      serviceId,
      files: [
        { path: 'main.py',          content: toB64(code) },
        { path: 'requirements.txt', content: toB64(requirements) },
        { path: 'Procfile',         content: toB64(procfile) },
      ],
    },
  })
}

export async function stopService(cfg: RailwayConfig, serviceId: string): Promise<void> {
  await gql(cfg.apiToken, `
    mutation serviceInstanceDeploy($serviceId: String!, $projectId: String!) {
      serviceInstanceDeploy(serviceId: $serviceId, projectId: $projectId)
    }
  `, { serviceId, projectId: cfg.projectId })
}

export async function deployBot(
  cfg: RailwayConfig,
  name: string,
  code: string,
  botToken: string,
): Promise<DeployResult> {
  const serviceId = await createService(cfg.apiToken, cfg.projectId, name)
  await setEnvVar(cfg.apiToken, cfg.projectId, serviceId, 'BOT_TOKEN', botToken)
  await deployCode(cfg.apiToken, serviceId, code)

  return {
    serviceId,
    dashboardUrl: `https://railway.app/project/${cfg.projectId}/service/${serviceId}`,
  }
}
