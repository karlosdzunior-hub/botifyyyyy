import { LLM_SYSTEM_PROMPT } from '../config.js'

interface LLMConfig {
  provider: string
  apiKey: string
  model?: string
}

const PROVIDERS: Record<string, { baseUrl: string; defaultModel: string }> = {
  openai: { baseUrl: 'https://api.openai.com/v1',                         defaultModel: 'gpt-4o' },
  groq:   { baseUrl: 'https://api.groq.com/openai/v1',                    defaultModel: 'llama-3.3-70b-versatile' },
  qwen:   { baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', defaultModel: 'qwen-plus' },
}

export async function generateBotCode(description: string, cfg: LLMConfig): Promise<string> {
  const provider = PROVIDERS[cfg.provider] ?? PROVIDERS.openai
  const model    = cfg.model || provider.defaultModel

  const res = await fetch(`${provider.baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${cfg.apiKey}`,
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      messages: [
        { role: 'system', content: LLM_SYSTEM_PROMPT },
        { role: 'user',   content: `Создай бота: ${description}` },
      ],
    }),
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`LLM error ${res.status}: ${err}`)
  }

  const json = (await res.json()) as { choices: { message: { content: string } }[] }
  let code = json.choices[0].message.content.trim()

  if (code.startsWith('```python')) code = code.slice(9)
  if (code.startsWith('```'))       code = code.slice(3)
  if (code.endsWith('```'))         code = code.slice(0, -3)

  return code.trim()
}
