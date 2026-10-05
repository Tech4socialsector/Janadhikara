<template>
  <div class="flex h-screen flex-col bg-white dark:bg-gray-900 lg:flex-row">
    <div class="relative flex flex-shrink-0 flex-col justify-between overflow-hidden bg-gradient-to-br from-gray-900 to-gray-700 p-6 text-white sm:p-8 lg:w-1/2 lg:justify-between lg:p-12">
      <div class="flex items-center gap-3">
        <img
          :src="loginLogo"
          alt=""
          class="login-logo h-16 w-16 flex-shrink-0 object-contain drop-shadow-lg sm:h-20 sm:w-20 lg:h-24 lg:w-24"
        />
        <span class="login-rise text-xl font-semibold lg:text-2xl" style="--d: 0.25s">{{ brandingResource.data?.app_name || 'Janadhikara' }}</span>
      </div>

      <div class="login-rise mt-6 max-w-sm lg:mt-0" style="--d: 0.4s">
        <h2 class="text-xl font-semibold leading-tight sm:text-2xl lg:text-3xl">
          {{ brandingResource.data?.login_headline || 'Care coordination for every household you serve.' }}
        </h2>
        <p class="mt-2 hidden text-sm text-white/70 sm:block lg:mt-4">
          {{ brandingResource.data?.login_description || 'Track visits, follow-ups, and growth monitoring in one place — built for community health workers on the ground.' }}
        </p>
      </div>

      <p class="login-rise mt-6 hidden text-xs text-white/40 lg:mt-0 lg:block" style="--d: 0.7s">
        &copy; {{ new Date().getFullYear() }} {{ brandingResource.data?.app_name || 'Janadhikara' }}
        <template v-if="appVersion"> &middot; Version {{ appVersion }}</template>
      </p>

      <div class="login-drift pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-white/5 lg:-right-24 lg:-top-24 lg:h-72 lg:w-72" />
      <div class="login-drift login-drift-alt pointer-events-none absolute -bottom-24 -left-12 h-64 w-64 rounded-full bg-white/5 lg:-bottom-32 lg:-left-16 lg:h-80 lg:w-80" />
    </div>

    <div class="flex flex-1 items-center justify-center overflow-y-auto bg-gray-50 px-6 py-8 dark:bg-gray-950 sm:px-8">
      <div class="w-full max-w-sm">
        <h1 class="login-rise text-xl font-semibold text-gray-900 dark:text-gray-100 sm:text-2xl" style="--d: 0.15s">Welcome back</h1>
        <p class="login-rise mt-1 text-sm text-gray-500 dark:text-gray-400" style="--d: 0.25s">Log in to continue to your dashboard.</p>

        <form
          v-if="showPasswordForm"
          style="--d: 0.35s"
          class="login-rise mt-6 flex flex-col gap-5 rounded-2xl border border-gray-200 bg-white p-6 shadow-lg shadow-gray-200/60 dark:border-gray-800 dark:bg-gray-900 dark:shadow-none sm:mt-8 sm:p-7"
          @submit.prevent="submit"
        >
          <FormControl
            type="text"
            label="Email"
            v-model="email"
            autocomplete="username"
            required
          />
          <div>
            <FormControl
              :type="showPassword ? 'text' : 'password'"
              label="Password"
              v-model="password"
              autocomplete="current-password"
              required
            >
              <template #suffix>
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  tabindex="-1"
                  :icon="showPassword ? 'eye-off' : 'eye'"
                  :tooltip="showPassword ? 'Hide password' : 'Show password'"
                  @click="showPassword = !showPassword"
                />
              </template>
            </FormControl>
            <Button variant="ghost" size="sm" class="mt-1 !px-0" type="button" @click="openForgotPassword">
              Forgot password?
            </Button>
          </div>
          <ErrorMessage :message="loginResource.error" />
          <Button icon-left="log-in" variant="solid" :loading="loginResource.loading" type="submit" size="lg">
            Log in
          </Button>
        </form>

        <!-- Single sign-on: one frappe-ui button per enabled Social Login Key
        (Frappe's own provider list - see janadhikara.api.get_login_options).
        Sign-in always lands on Home. -->
        <div v-if="providers.length" class="login-rise" style="--d: 0.5s" :class="showPasswordForm ? 'mt-5' : 'mt-6 sm:mt-8'">
          <div v-if="showPasswordForm" class="mb-4 flex items-center gap-3 text-xs text-gray-400">
            <span class="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
            or
            <span class="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
          </div>
          <div class="flex flex-col gap-2.5">
            <Button
              v-for="provider in providers"
              :key="provider.name"
              variant="outline"
              size="lg"
              class="w-full"
              :loading="redirectingTo === provider.name"
              @click="signInWith(provider)"
            >
              <template v-if="isImageUrl(provider.icon)" #prefix>
                <img :src="provider.icon" :alt="provider.label" class="h-4 w-4" />
              </template>
              Continue with {{ provider.label }}
            </Button>
          </div>
        </div>
        <p v-if="appVersion" class="login-rise mt-6 text-center text-xs text-gray-400 dark:text-gray-500" style="--d: 0.7s">
          Version {{ appVersion }}
        </p>
      </div>
    </div>

    <Dialog v-model="showForgotPassword" :options="{ title: 'Reset Password' }">
      <template #body-content>
        <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Enter your email and we'll send you a link to reset your password.
        </p>
        <FormControl
          type="text"
          label="Email"
          v-model="resetEmail"
          autocomplete="username"
          required
        />
        <ErrorMessage class="mt-3" :message="resetError" />
        <p v-if="resetSent" class="mt-3 text-sm text-green-600 dark:text-green-400">
          If that email is registered with us, a reset link is on its way. Please check your inbox.
        </p>
      </template>
      <template #actions>
        <div class="flex w-full justify-end gap-2">
          <Button icon-left="x" @click="showForgotPassword = false" size="sm">Close</Button>
          <Button icon-left="send" variant="solid" :loading="resetLoading" @click="submitForgotPassword" size="sm">
            Send reset link
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { FormControl, Button, ErrorMessage, Dialog, FeatherIcon, call, useCall } from 'frappe-ui'
import { loginResource } from '@/data/session'
import { brandingResource, DEFAULT_LOGO } from '@/data/branding'

// This panel's background (bg-gradient-to-br from-gray-900 to-gray-700
// above) is permanently dark regardless of the app's light/dark theme
// toggle, so it always wants the dark-mode logo rather than following
// currentTheme like the sidebar/mobile shell header do.
// Single sign-on providers enabled in Social Login Key (public - this page is
// shown before anyone is logged in).
const loginOptions = useCall({
  url: '/api/v2/method/janadhikara.api.get_login_options',
  method: 'GET',
  cacheKey: 'janadhikara-login-options',
})
const providers = computed(() => loginOptions.data?.providers || [])
const appVersion = computed(() => loginOptions.data?.app_version || '')
// "Disable user/password login" in System Settings hides the form - but only
// when there is at least one other way in, so nobody is left with a blank page.
const showPasswordForm = computed(() => !(loginOptions.data?.disable_user_pass_login && providers.value.length))
const redirectingTo = ref(null)
function signInWith(provider) {
  redirectingTo.value = provider.name
  window.location.href = provider.auth_url
}
const isImageUrl = (icon) => typeof icon === 'string' && /^(https?:)?\/|^data:image/.test(icon)

const loginLogo = computed(() => brandingResource.data?.app_logo_dark || brandingResource.data?.app_logo || DEFAULT_LOGO)

const email = ref('')
const password = ref('')
const showPassword = ref(false)

// Trimmed only at submit time, not on every keystroke via v-model - a
// pasted credential often carries a stray leading/trailing space (copied
// from an email, a chat message, a password manager's clipboard entry),
// which Frappe's login compares byte-for-byte and silently rejects as
// wrong. Trimming while typing would be actively wrong instead: it'd fight
// a user who legitimately types a trailing space mid-edit. Only the outer
// whitespace is stripped either way - a real space in the middle of an
// email local-part or password stays intact.
function submit() {
  loginResource.submit({ email: email.value.trim(), password: password.value.trim() })
}

const showForgotPassword = ref(false)
const resetEmail = ref('')
const resetError = ref(null)
const resetSent = ref(false)
const resetLoading = ref(false)

function openForgotPassword() {
  resetEmail.value = email.value
  resetError.value = null
  resetSent.value = false
  showForgotPassword.value = true
}

async function submitForgotPassword() {
  const user = resetEmail.value.trim()
  if (!user) return
  resetLoading.value = true
  resetError.value = null
  resetSent.value = false
  try {
    await call('frappe.core.doctype.user.user.reset_password', { user })
    resetSent.value = true
  } catch (e) {
    resetError.value = e
  } finally {
    resetLoading.value = false
  }
}
</script>

<style scoped>
/* Entrance: each piece rises and fades in, staggered with --d. */
.login-rise {
  opacity: 0;
  animation: login-rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) var(--d, 0s) forwards;
}
@keyframes login-rise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* The logo pops in, then floats gently. */
.login-logo {
  animation:
    login-pop 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both,
    login-float 6s ease-in-out 0.8s infinite;
}
@keyframes login-pop {
  from {
    opacity: 0;
    transform: scale(0.7) rotate(-6deg);
  }
  to {
    opacity: 1;
    transform: scale(1) rotate(0);
  }
}
@keyframes login-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

/* The two background discs breathe and drift, slowly enough to stay calm. */
.login-drift {
  animation: login-drift 14s ease-in-out infinite alternate;
}
.login-drift-alt {
  animation-duration: 18s;
  animation-direction: alternate-reverse;
}
@keyframes login-drift {
  from {
    transform: translate(0, 0) scale(1);
  }
  to {
    transform: translate(18px, 14px) scale(1.12);
  }
}

/* No motion for anyone who's asked their system for less of it. */
@media (prefers-reduced-motion: reduce) {
  .login-rise,
  .login-logo,
  .login-drift {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
</style>
