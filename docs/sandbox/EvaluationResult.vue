<template>
  <div class="leading-loose text-sm tracking-wide">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <div class="flex items-center gap-x-2">
        <span>
          Depth: {{ depth }}
          <template v-if="maxDepth !== null">
            / {{ maxDepth }}
          </template>
        </span>

        <div class="flex items-center gap-x-1">
          <button
            class="cursor-pointer hover:text-(--vp-code-color)! disabled:opacity-40 disabled:pointer-events-none"
            title="Increase depth"
            :disabled="maxDepth !== null && depth >= maxDepth"
            @click="onIncrementClick"
          >
            <svg class="size-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
          </button>

          <button
            class="cursor-pointer hover:text-(--vp-code-color)!"
            title="Decrease depth"
            @click="onDecrementClick"
          >
            <svg class="size-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>
          </button>
        </div>
      </div>

      <div>
      Evaluations: {{ (evaluation?.evaluations ?? 0).toLocaleString() }}
      </div>

      <div>
        Duration: {{ (evaluation?.duration ?? 0).toFixed(0) }}ms
      </div>

      <div>
        Speed: {{ ((evaluation?.evaluations ?? 0) / (evaluation?.duration ?? 1)).toFixed(1) }} evals/ms
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { SearchResult } from './use-engine'

const props = defineProps<{
  depth: number
  maxDepth?: number | null
  evaluation?: SearchResult | null
}>()

const depth = defineModel<number>('depth', { required: true })

const maxDepth = computed(() => props.maxDepth ?? null)

function onIncrementClick() {
  if (maxDepth.value !== null) {
    depth.value = Math.min(depth.value + 1, maxDepth.value)
    return
  }

  depth.value++
}

function onDecrementClick() {
  depth.value = Math.max(depth.value - 1, 1)
}
</script>