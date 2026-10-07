import { reactive, ref } from 'vue'
import { useCall } from 'frappe-ui'

export const assistantState = reactive({
  visible: false,
})

export function toggleAssistant() {
  assistantState.visible = !assistantState.visible
}

// Cheap, safe-for-every-user check: is the assistant on, and what's it
// called. Never includes the base URL, model, or key - see
// janadhikara.ai.assistant.get_assistant_config.
export const assistantConfigResource = useCall({
  url: '/api/v2/method/janadhikara.ai.assistant.get_assistant_config',
  method: 'GET',
  cacheKey: 'janadhikara-ai-assistant-config',
})

// Conversation lives here (not local to the panel component) so closing and
// reopening the panel within a session doesn't lose context - mirrors
// notificationsState living outside NotificationPanel.vue.
export const conversation = ref([])
// What is sent back to the server each turn: the same conversation, but with placeholders where the
// assistant mentioned a person's details. The model never sees those values; the real ones are put into
// `conversation` (what is shown) by the server.
const history = ref([])

export function clearAssistantConversation() {
  conversation.value = []
  history.value = []
}

const sendMessageCall = useCall({
  url: '/api/v2/method/janadhikara.ai.assistant.send_message',
  method: 'POST',
  immediate: false,
})

export async function sendAssistantMessage(message) {
  const result = await sendMessageCall.submit({
    messages: history.value,
    message,
  })
  history.value = result.messages
  conversation.value = [
    ...conversation.value,
    { role: 'user', content: message },
    { role: 'assistant', content: result.reply },
  ]
  return result
}

export const sending = sendMessageCall
