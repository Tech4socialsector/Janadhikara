<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ pageTitle }}</h1>
      </template>
      <template #actions>
        <Button
          v-if="metaResource.data"
          variant="solid"
          @click="goToNew"
        >
          <template #prefix>
            <FeatherIcon name="plus" class="h-4 w-4" />
          </template>
          New
        </Button>
      </template>
    </PageHeader>

    <div v-if="metaResource.loading && !metaResource.data" class="space-y-2">
      <Skeleton v-for="i in 5" :key="i" height="2.5rem" />
    </div>
    <ErrorMessage v-else-if="metaResource.error" :message="metaResource.error" />

    <template v-else-if="metaResource.data">
      <!-- Toolbar: refresh, Filter/Sort/Columns, always above the list on
      both desktop and mobile - desktop opens FilterEditor/SortEditor/the
      column picker in an anchored Popover, mobile opens Filter/Sort in a
      bottom sheet Dialog instead (screen-space and touch-target reasons;
      the column picker stays a Popover even on mobile - it's a short,
      one-off list, not worth a full sheet). All three write to state
      shared across the toolbar and the quick-filter row below, so
      switching between them (e.g. rotating a tablet) never loses what
      was set.

      :hide-on-blur="false" on all three - each one's own content
      (FilterEditor/SortEditor/the column checkboxes) opens its own nested
      Select dropdown, whose options render through reka-ui's own portal
      to document.body - outside this Popover's DOM subtree. Popover.vue's
      default onInteractOutside treats that portal click as "outside" and
      closes the whole Popover before the nested Select can finish
      opening, so its options never appeared (confirmed live: clicking a
      filter row's value dropdown did nothing). false disables that
      auto-close; each Popover still closes normally via its own trigger
      toggle or Escape. -->
      <!-- Mobile-only global search - desktop already has one quick-filter
      text box per visible column just below the toolbar (see the
      !isMobile block right after this one), which mobile deliberately
      hides (no room for N separate boxes on a phone). That left mobile
      with no way to free-text search a list at all, only the Filter
      sheet's field-by-field FilterEditor. Searches row.name (the record's
      own ID) via `like`, same field cardTitle() above shows as the
      card's own title - for the field:X-autonamed doctypes this app
      mostly uses (confirmed live: AI Guide Section, App Module Setting),
      that's already the human-readable title, so this is a real search
      by name/title, not just an opaque ID lookup. Feeds listFilters the
      same way quickFilters/advancedFilters do (see searchFilter below),
      so it composes with whatever's set in the Filter sheet rather than
      replacing it. -->
      <div v-if="isMobile" class="relative mb-2">
        <FeatherIcon name="search" class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search records"
          class="h-10 w-full rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-300 focus:outline-none focus:ring-1 focus:ring-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500"
        />
      </div>

      <div class="mb-3 flex items-center justify-end gap-2">
        <Tooltip text="Refresh">
          <button
            class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
            :disabled="rows.loading"
            @click="refreshList"
          >
            <FeatherIcon name="refresh-cw" class="h-3.5 w-3.5" :class="{ 'animate-spin': rows.loading }" />
          </button>
        </Tooltip>

        <template v-if="!isMobile">
          <Popover placement="bottom-end" popover-class="doctype-list-popover" :hide-on-blur="false">
            <template #target="{ togglePopover }">
              <button
                class="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300"
                :class="hasActiveFilters ? 'border-gray-900 dark:border-gray-100' : 'border-gray-200'"
                @click="togglePopover"
              >
                <FeatherIcon name="filter" class="h-3.5 w-3.5" />
                Filter
                <span
                  v-if="activeFilterCount"
                  class="flex h-4 min-w-4 items-center justify-center rounded-full bg-gray-900 px-1 text-[10px] text-white dark:bg-gray-100 dark:text-gray-900"
                >
                  {{ activeFilterCount }}
                </span>
              </button>
            </template>
            <template #body-main>
              <div class="w-[26rem] max-w-[90vw] p-3">
                <FilterEditor :fields="allFields" v-model="advancedFilters" />
              </div>
            </template>
          </Popover>

          <Popover placement="bottom-end" popover-class="doctype-list-popover" :hide-on-blur="false">
            <template #target="{ togglePopover }">
              <button
                class="flex items-center gap-1.5 rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300"
                @click="togglePopover"
              >
                <FeatherIcon name="sliders" class="h-3.5 w-3.5" />
                Sort
              </button>
            </template>
            <template #body-main>
              <div class="w-72 max-w-[90vw] p-3">
                <SortEditor :fields="allFields" v-model="sortValue" />
              </div>
            </template>
          </Popover>
        </template>

        <template v-else>
          <button
            class="flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300"
            :class="hasActiveFilters ? 'border-gray-900 dark:border-gray-100' : 'border-gray-200'"
            @click="showFilterSheet = true"
          >
            <FeatherIcon name="filter" class="h-3.5 w-3.5" />
            Filter
            <span
              v-if="activeFilterCount"
              class="flex h-4 min-w-4 items-center justify-center rounded-full bg-gray-900 px-1 text-[10px] text-white dark:bg-gray-100 dark:text-gray-900"
            >
              {{ activeFilterCount }}
            </span>
          </button>
          <button
            class="flex items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300"
            @click="showSortSheet = true"
          >
            <FeatherIcon name="sliders" class="h-3.5 w-3.5" />
            Sort
          </button>
        </template>

        <Popover placement="bottom-end" popover-class="doctype-list-popover" :hide-on-blur="false">
          <template #target="{ togglePopover }">
            <button
              class="flex items-center gap-1.5 rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300"
              @click="togglePopover"
            >
              <FeatherIcon name="columns" class="h-3.5 w-3.5" />
              Columns
            </button>
          </template>
          <template #body-main>
            <div class="max-h-80 w-56 overflow-y-auto p-2">
              <label
                v-for="field in allFields"
                :key="field.fieldname"
                class="flex items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                <input
                  type="checkbox"
                  class="form-checkbox h-4 w-4 !rounded-[3px] border-gray-300 dark:border-gray-600 dark:bg-gray-800"
                  :checked="!hiddenFieldnames.has(field.fieldname)"
                  @change="toggleColumnVisible(field.fieldname)"
                />
                {{ field.label }}
              </label>
            </div>
          </template>
        </Popover>
      </div>

      <!-- Quick filter row - one plain text/select box per visible column,
      always on screen (unlike the Filter popover above, which needs a
      click to open) for the common case of "just narrow this one column
      by typing" - same idea as Helpdesk's own per-column filter boxes.
      Writes to quickFilters, kept separate from the Filter popover's own
      advancedFilters so an operator/multi-field filter set there isn't
      silently overwritten by a quick box here for the same field, or vice
      versa - listFilters (what actually reaches the API) merges both,
      with advancedFilters taking precedence on any field both touch. -->
      <div v-if="!isMobile" class="mb-3 flex flex-wrap gap-2">
        <div v-for="col in visibleColumns" :key="col.fieldname" class="w-40 flex-shrink-0">
          <FormControl
            v-if="col.fieldtype === 'Select'"
            type="select"
            class="[&_[data-slot=trigger]]:w-full"
            :options="[{ label: col.label, value: '' }, ...selectOptions(col)]"
            v-model="quickFilters[col.fieldname]"
          />
          <FormControl
            v-else-if="col.fieldtype === 'Check'"
            type="select"
            class="[&_[data-slot=trigger]]:w-full"
            :options="[{ label: col.label, value: '' }, { label: 'Yes', value: '1' }, { label: 'No', value: '0' }]"
            v-model="quickFilters[col.fieldname]"
          />
          <FormControl
            v-else
            type="text"
            :placeholder="col.label"
            v-model="quickFilters[col.fieldname]"
          />
        </div>
      </div>

      <Dialog v-model="showFilterSheet" :options="{ size: 'sm', title: 'filter-sheet' }">
        <template #body>
          <div class="filter-sheet-panel flex flex-col">
            <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800">
              <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Filter</h3>
              <button
                class="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                @click="showFilterSheet = false"
              >
                <FeatherIcon name="x" class="h-4 w-4" />
              </button>
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
              <FilterEditor :fields="allFields" v-model="advancedFilters" @update:model-value="showFilterSheet = false" />
            </div>
          </div>
        </template>
      </Dialog>

      <Dialog v-model="showSortSheet" :options="{ size: 'sm', title: 'sort-sheet' }">
        <template #body>
          <div class="filter-sheet-panel flex flex-col">
            <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800">
              <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Sort</h3>
              <button
                class="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                @click="showSortSheet = false"
              >
                <FeatherIcon name="x" class="h-4 w-4" />
              </button>
            </div>
            <div class="px-4 py-4">
              <SortEditor :fields="allFields" v-model="sortValue" />
            </div>
          </div>
        </template>
      </Dialog>

      <Dialog
        v-model="showBulkDeleteConfirm"
        :options="{
          title: `Delete ${selectedNames.length} record${selectedNames.length === 1 ? '' : 's'}?`,
          message: 'This cannot be undone.',
          icon: { name: 'alert-triangle', appearance: 'danger' },
          actions: [
            { label: 'Delete', variant: 'solid', theme: 'red', onClick: doBulkDelete },
            { label: 'Cancel' },
          ],
        }"
      />

      <div v-if="rows.loading && !rows.data" class="space-y-2">
        <Skeleton v-for="i in 5" :key="i" height="2.5rem" />
      </div>
      <ErrorMessage v-else-if="rows.error" :message="rows.error" />
      <!-- No separate hand-built empty state here on desktop - ListView's
      own emptyState option (listViewOptions, in script) covers that,
      rendered internally by its ListEmptyState when rows.length is 0.
      Mobile has no such built-in (it's a plain card list, not ListView),
      so it keeps its own empty-state block just below. -->
      <div
        v-else-if="isMobile && allRows.length === 0"
        class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-gray-200 py-16 text-center dark:border-gray-800"
      >
        <span class="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
          <FeatherIcon name="inbox" class="h-5 w-5 text-gray-400 dark:text-gray-500" />
        </span>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          {{ hasActiveFilters ? 'No records match your filters.' : 'No records yet.' }}
        </p>
        <Button v-if="hasActiveFilters" variant="ghost" @click="clearAllFilters">
          Clear filters
        </Button>
        <Button v-else-if="metaResource.data" variant="outline" @click="goToNew">
          <template #prefix>
            <FeatherIcon name="plus" class="h-4 w-4" />
          </template>
          Create the first one
        </Button>
      </div>

      <!-- Mobile: a table forces horizontal scrolling to see anything past
      the first column or two, which is awkward on a phone - each row
      becomes its own card instead, with the record's title/ID as the
      card's title and every in_list_view column shown as a label/value
      line below it.

      Title is cardTitle(row) - meta.title_field when the doctype declares
      one, else row.name (the record's own ID) - not visibleColumns[0].
      That used to make whatever field happened to be first in list-view
      column order the title (e.g. AI Guide Section's "Enabled" checkbox,
      since in_list_view fields render in field_order), which read oddly
      as a card heading and had nothing to do with actually identifying
      the record. name is a meaningful title for most doctypes here since
      they're autoname: field:X (confirmed live - AI Guide Section's name
      already equals its own Section Name).

      Body list is `columns` (every in_list_view field), not
      `visibleColumns` (desktop's Columns-popover-filtered subset) - hiding
      a column from the dense desktop table is a "less clutter" choice
      that doesn't apply to a mobile card, which only ever shows one
      record at a time and has the room. The title field itself is
      excluded from the body loop so it isn't shown twice when it's also
      one of the in_list_view columns. -->
      <div v-if="showResults && isMobile" class="space-y-2">
        <div
          v-for="row in allRows"
          :key="row.name"
          class="flex cursor-pointer items-start gap-2 rounded-lg border p-3 shadow-sm transition-shadow active:shadow-none dark:border-gray-800"
          :style="cardAccentStyle(row)"
          @click="goToRow(row.name)"
        >
          <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
              {{ cardTitle(row) }}
            </div>
            <div v-if="cardBodyColumnsFor(row).length" class="mt-1.5 space-y-1">
              <div
                v-for="col in cardBodyColumnsFor(row)"
                :key="col.fieldname"
                class="flex items-baseline justify-between gap-3 text-sm"
              >
                <span class="flex-shrink-0 text-gray-500 dark:text-gray-400">{{ col.label }}</span>
                <span class="truncate text-right text-gray-700 dark:text-gray-300">
                  <span
                    v-if="isStatusLikeField(col) && row[col.fieldname]"
                    class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="statusBadgeClasses(row[col.fieldname])"
                  >
                    {{ row[col.fieldname] }}
                  </span>
                  <UserLinkHoverCard v-else-if="isUserLink(col) && row[col.fieldname]" :user="row[col.fieldname]" @click.stop>
                    <span class="underline decoration-dotted">{{ row[col.fieldname] }}</span>
                  </UserLinkHoverCard>
                  <template v-else>{{ formatValue(row[col.fieldname], col) }}</template>
                </span>
              </div>
            </div>
          </div>
          <FeatherIcon name="chevron-right" class="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-300 dark:text-gray-600" />
        </div>
      </div>

      <!-- Desktop: frappe-ui's own ListView/ListFooter - the exact
      components Frappe Helpdesk's ticket list (ListViewBuilder.vue) is
      built on, rather than a hand-rolled table approximating the same
      look. Comes with checkbox selection (incl. shift-click range
      select), a floating select-banner, sticky/resizable columns, and
      row hover/active states out of the box - all previously hand-built
      here and prone to exactly the kind of edge-case bugs a
      battle-tested shared component has already had shaken out of it. -->
      <!-- No default-slot override here (that slot is what renders
      ListHeader/ListRows/ListEmptyState/ListSelectBanner internally in
      ListView.vue - replacing it, as an earlier version of this did,
      means reimplementing that whole chain by hand, and a first attempt
      at that left the row-render loop out entirely, showing a header
      with zero rows). Customizing per-cell rendering instead happens via
      the #cell slot, which ListRow.vue picks up itself through
      list.slots.cell (list = ListView's own useSlots()) - no override of
      ListRows/ListRow's own internals needed for that. The select-banner
      actions still need a default-slot override, since ListView.vue's
      own default content doesn't forward anything to ListSelectBanner -
      but the row-rendering chain above it (ListHeader/ListRows/
      ListEmptyState) is reproduced as-is from ListView.vue so nothing
      about that other than the #cell slot passthrough changes. -->
      <ListView
        v-if="!isMobile"
        class="mt-1"
        :columns="listViewColumns"
        :rows="allRows"
        row-key="name"
        :options="listViewOptions"
        @update:selections="(sel) => (selectedNames = Array.from(sel))"
      >
        <template #cell="{ column, row, item }">
          <ListRowItem :column="column" :row="row" :item="formatValue(item, column.docField)" v-slot="{ label }">
            <span
              v-if="isStatusLikeField(column.docField) && item"
              class="inline-flex items-center gap-1.5"
            >
              <span class="h-2 w-2 flex-shrink-0 rounded-full" :style="{ backgroundColor: statusBorderColor(item) }" />
              <span class="truncate text-base">{{ item }}</span>
            </span>
            <UserLinkHoverCard v-else-if="isUserLink(column.docField) && item" :user="item" @click.stop>
              <span class="truncate text-base underline decoration-dotted">{{ item }}</span>
            </UserLinkHoverCard>
            <div v-else class="truncate text-base">{{ label }}</div>
          </ListRowItem>
        </template>
        <template #default="{ showGroupedRows, selectable }">
          <ListHeader />
          <template v-if="allRows.length">
            <ListGroups v-if="showGroupedRows" />
            <ListRows v-else />
          </template>
          <ListEmptyState v-else />
          <ListSelectBanner v-if="selectable">
            <template #actions>
              <Button variant="solid" theme="red" @click="confirmBulkDelete">
                <template #prefix>
                  <FeatherIcon name="trash-2" class="h-4 w-4" />
                </template>
                Delete
              </Button>
            </template>
          </ListSelectBanner>
        </template>
      </ListView>

      <!-- Load More + count + page-size selector, replacing Previous/Next.
      The first 20 rows come from `rows` (useList); every click past that
      goes through the separate loadMoreResource/moreRows accumulator (see
      script - useList's own limit can't change after creation, so a
      variable page size needs its own fetch path). The size buttons only
      change what the *next* Load More click fetches, not a reset of what's
      already showing - a deliberate simplification, not an oversight.
      totalCount is a separate lightweight get_count call (frappe.get_list's
      own paged response carries no total, only has_next_page) purely for
      the "X of Y" label, not used for the fetch/pagination logic itself. -->
      <ListFooter
        v-if="!isMobile && showResults"
        class="mt-4"
        :model-value="pageSize"
        :options="{ rowCount: allRows.length, totalCount: totalCountResource.data ?? 0, pageLengthOptions: PAGE_SIZE_OPTIONS }"
        @update:model-value="setPageSize"
        @load-more="loadMore"
      />
    </template>
  </AppLayout>
</template>

<style>
/* Same data-dialog hook pattern as SettingsDialog.vue/ChildTable.vue's
row editor. Only used on mobile (the Filter/Sort pills that open these are
isMobile-gated in the template), so both are bottom sheets outright rather
than a centered-card/full-screen split by breakpoint like those - anchored
to the bottom edge and rounded only on top, matching the conventional
mobile filter-sheet affordance instead of a dialog that happens to fill
the screen. Selector covers both filter-sheet and sort-sheet, same
treatment for each. */
/* 1050, not 50 - see LinkField.vue's quick-create dialog for why: Leaflet's
own stylesheet puts its control pane at z-index 1000, which would paint
through a lower dialog z-index. */
[data-dialog='filter-sheet'].dialog-overlay,
[data-dialog='sort-sheet'].dialog-overlay {
  z-index: 1050;
}
[data-dialog='filter-sheet'].dialog-overlay > div,
[data-dialog='sort-sheet'].dialog-overlay > div {
  align-items: flex-end;
  padding: 0;
}
[data-dialog='filter-sheet'] .dialog-content,
[data-dialog='sort-sheet'] .dialog-content {
  margin: 0;
  max-width: none;
  width: 100vw;
  border-radius: 1rem 1rem 0 0;
}

/* Desktop's Filter/Sort Popover (see popover-class="doctype-list-popover"
above) has no elevation of its own beyond frappe-ui's default shadow-xl -
next to nearby page content (e.g. the bulk-select bar right below the
Sort button) that default reads as "part of the layout" rather than a
panel floating above it. A visibly stronger shadow (plus a hairline ring
frappe-ui's own border alone doesn't quite give against a white
background) makes the overlay read clearly as floating, without changing
its position/behavior - scoped to this page's own popovers via
popover-class rather than frappe-ui's shared body-container class, so
other Popovers elsewhere (e.g. UserHoverCard) are unaffected. */
.doctype-list-popover > div {
  box-shadow: 0 12px 32px -8px rgb(15 23 42 / 0.22), 0 0 0 1px rgb(15 23 42 / 0.04);
}
:global(.dark) .doctype-list-popover > div {
  box-shadow: 0 12px 32px -8px rgb(0 0 0 / 0.55), 0 0 0 1px rgb(255 255 255 / 0.06);
}

/* A FormControl type="select" nested inside one of these Popovers (the
Filter row's value dropdown, the Sort row's field dropdown) renders its
own dropdown via reka-ui's SelectPortal - straight to document.body, same
as the Popover's own content, so nesting doesn't nest their DOM (a
.doctype-list-popover descendant selector can't reach it). This needed a
[data-slot='content'][data-state='open'] z-index override the same way
ChildTable.vue's row-editor Dialog later turned out to (a Select nested
inside a Dialog hit the identical bug) - moved to index.css so both (and
anywhere else this comes up) share one rule instead of two copies that
could drift. See index.css for the actual rule and the full writeup of
why it's needed. */

.filter-sheet-panel {
  width: 100%;
  max-height: 75vh;
}
</style>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import {
  useList,
  useCall,
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  FormControl,
  ListView,
  ListHeader,
  ListRows,
  ListRowItem,
  ListGroups,
  ListEmptyState,
  ListSelectBanner,
  ListFooter,
  Popover,
  Tooltip,
} from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import UserLinkHoverCard from '@/components/UserLinkHoverCard.vue'
import FilterEditor from '@/components/FilterEditor.vue'
import SortEditor from '@/components/SortEditor.vue'
import Skeleton from '@/components/Skeleton.vue'
import { useMeta, useListFields, useFormFields } from '@/data/useMeta'
import { findModuleByRoute } from '@/data/modules'
import { setPageTitle } from '@/data/pageTitle'
import { isStatusLikeField, statusBadgeClasses, statusBorderColor } from '@/utils/statusColors'

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('sm')

const props = defineProps({
  doctype: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()

const metaResource = useMeta(props.doctype)
const columns = useListFields(metaResource)
// Every real field on the doctype, not just in_standard_filter ones - the
// "+ Add a Filter" row and the Columns picker both let a user explicitly
// pick any field, the same way Frappe desk's own filter/column pickers
// aren't limited to a preconfigured subset.
const allFields = useFormFields(metaResource)

// Which of `columns` are actually shown, in both the desktop table and
// the mobile card view - defaults to all of them, narrowed via the
// Columns popover. Kept separate from `columns` itself (which still
// drives what fields are fetched from the server) so toggling visibility
// is instant and doesn't require a refetch.
//
// A plain computed with an internal override map, rather than a watch
// that assigns visibleFieldnames.value directly - `columns` starts empty
// before metaResource.data resolves and then changes again once it does,
// and a watch-driven ref update on that second change lands as its own
// separate reactive tick from rows' own columns.value.length-driven
// refetch, which raced useFetch's own abort-on-URL-change and leaked an
// AbortError into rows.error (visible above the table in production).
// Deriving visibility instead of assigning it collapses both `columns`
// changes and any visibility toggle into the same recomputation, so
// there's only ever one dependent state change per tick, not two.
const hiddenFieldnames = ref(new Set())
const visibleColumns = computed(() =>
  columns.value.filter((c) => !hiddenFieldnames.value.has(c.fieldname)),
)
function toggleColumnVisible(fieldname) {
  const next = new Set(hiddenFieldnames.value)
  if (next.has(fieldname)) {
    next.delete(fieldname)
  } else {
    next.add(fieldname)
  }
  hiddenFieldnames.value = next
}

// Two independent filter sources feeding the same query:
// - quickFilters: the always-visible per-column boxes below the toolbar
//   (Helpdesk-style quick filtering), one plain value per column, always
//   an exact/like match depending on fieldtype - see quickFilterEntries.
// - advancedFilters: the Filter popover/sheet's FilterEditor state (any
//   field, any operator, already in frappe.get_list's [operator, value]
//   shape).
// advancedFilters wins on any field both happen to set, since it's the
// more deliberate, explicit action of the two.
const quickFilters = reactive({})
const advancedFilters = ref({})
const searchQuery = ref('')

function selectOptions(field) {
  return (field.options || '')
    .split('\n')
    .map((v) => v.trim())
    .filter(Boolean)
    .map((v) => ({ label: v, value: v }))
}

const quickFilterEntries = computed(() => {
  const result = {}
  for (const col of visibleColumns.value) {
    const value = quickFilters[col.fieldname]
    if (value == null || value === '') continue
    if (col.fieldtype === 'Check') {
      result[col.fieldname] = Number(value)
    } else if (col.fieldtype === 'Select') {
      result[col.fieldname] = value
    } else {
      result[col.fieldname] = ['like', `%${value}%`]
    }
  }
  return result
})

// searchQuery goes last and wins on `name` if advancedFilters also
// happens to target it (unlikely in practice, but the same
// last-one-wins precedence quickFilters -> advancedFilters already uses
// above, just extended one step further).
const searchFilter = computed(() => {
  const q = searchQuery.value.trim()
  return q ? { name: ['like', `%${q}%`] } : {}
})
const listFilters = computed(() => ({ ...quickFilterEntries.value, ...advancedFilters.value, ...searchFilter.value }))
const hasActiveFilters = computed(() => Object.keys(listFilters.value).length > 0)
const activeFilterCount = computed(() => Object.keys(advancedFilters.value).length)

function clearAllFilters() {
  for (const key of Object.keys(quickFilters)) delete quickFilters[key]
  advancedFilters.value = {}
  searchQuery.value = ''
}

// Starts at the doctype's own declared default (sort_field/sort_order,
// e.g. AI Guide Section's sort_order asc) rather than a hardcoded
// "modified desc" - same default DoctypeList used before the Sort control
// existed. Only actually applied once metaResource.data resolves (see the
// watch below); until then rows' orderBy just falls back to this initial
// value, which is "modified desc" anyway.
const sortValue = ref({ field: 'modified', direction: 'desc' })
let sortDefaultInitialized = false
watch(
  () => metaResource.data,
  (meta) => {
    if (!meta || sortDefaultInitialized) return
    sortDefaultInitialized = true
    totalCountResource.fetch()
    sortValue.value = {
      field: meta.sort_field || 'modified',
      direction: (meta.sort_order || 'desc').toLowerCase(),
    }
  },
)

const pageTitle = findModuleByRoute(route.params.doctypeRoute)?.label || props.doctype
setPageTitle(pageTitle)

// `immediate: false` - metaResource.data (and the `columns`/`orderBy` it
// drives) isn't ready on mount, so an immediate fetch would run with the
// wrong fields/orderBy. useList's own useFetch already watches its computed
// URL and auto-refetches whenever it changes (refetch: true, the default) -
// since that URL is itself derived from columns.value/metaResource.data,
// the moment metaResource.data resolves is the moment the URL changes and
// this fires on its own. An explicit rows.fetch() call here used to race
// that same auto-refetch (both firing in the same tick, one aborting the
// other), leaking an AbortError into rows.error as "signal is aborted
// without reason" - removed rather than raced against.
//
// Fixed limit of 20 here regardless of the page-size selector - useList's
// own `limit` is captured once at creation with no reactive setter (see
// pageSize below for how "Load More" at a chosen size is actually done),
// so this instance only ever covers the first page. rows.delete (bulk
// delete) is the only other useList helper this file relies on, and that
// stays wired to this same instance regardless of which page a row came
// from - deleting by name doesn't care which fetch loaded it.
const rows = useList({
  doctype: props.doctype,
  fields: () => (columns.value.length ? ['name', ...columns.value.map((c) => c.fieldname)] : ['name']),
  filters: () => listFilters.value,
  orderBy: () => `${sortValue.value.field} ${sortValue.value.direction}`,
  limit: 20,
  immediate: false,
})

// "Load More" past the first page, at whatever size is currently selected
// (see PAGE_SIZE_OPTIONS/pageSize below) - a separate resource because
// useList's own next()/limit can't be resized after creation. moreRows
// accumulates across clicks the same way useList's own allData does
// (append, never replace) for exactly this list's own lifetime; a
// filter/sort/doctype change resets it via the watch below, same as the
// selection-clearing watch already does for selectedNames.
const PAGE_SIZE_OPTIONS = [20, 50, 100]
const pageSize = ref(20)
const moreRows = ref([])
const loadMoreResource = useCall({
  url: `/api/v2/document/${props.doctype}`,
  method: 'GET',
  params: () => ({
    fields: JSON.stringify(columns.value.length ? ['name', ...columns.value.map((c) => c.fieldname)] : ['name']),
    filters: JSON.stringify(listFilters.value),
    order_by: `${sortValue.value.field} ${sortValue.value.direction}`,
    start: 20 + moreRows.value.length,
    limit: pageSize.value,
  }),
  immediate: false,
})

function setPageSize(size) {
  pageSize.value = size
}

const hasExhaustedMore = ref(false)

async function loadMore() {
  // useCall's fetch() already unwraps to the v2 REST response's own
  // `.data` array (same shape useList's own allData accumulates) - no
  // separate unwrapping needed here.
  const newRows = (await loadMoreResource.fetch()) || []
  moreRows.value = [...moreRows.value, ...newRows]
  if (newRows.length < pageSize.value) hasExhaustedMore.value = true
}

watch([listFilters, sortValue, () => props.doctype], () => {
  moreRows.value = []
  hasExhaustedMore.value = false
})

const allRows = computed(() => [...(rows.data || []), ...moreRows.value])
// Once moreRows has ever been fetched, its own last batch is the only
// real signal of whether another page could exist - rows.hasNextPage
// reflects just the first 20-row page and goes stale the moment Load
// More is used even once.
const canLoadMore = computed(() =>
  moreRows.value.length > 0 ? !hasExhaustedMore.value : rows.hasNextPage,
)

// The mobile card view and the desktop table (template, below) each open
// their own `v-if` rather than chaining `v-else-if` off the loading/error/
// empty block above them, since they're structurally different elements
// (a plain list wrapper vs. a table) - that split previously let a
// transient rows.error (e.g. an aborted in-flight request) render its
// message ABOVE the table while the table kept rendering underneath it,
// instead of the error replacing the table the way the v-if chain above
// it implies. Both blocks gate on this single flag instead.
const showResults = computed(() => !rows.loading && !rows.error && allRows.value.length > 0)

// ListView's own column shape ({key, label, ...}) doesn't carry Frappe
// field metadata (fieldtype, options, ...) - docField keeps the original
// field object attached per column so isStatusLikeField/isUserLink/
// formatValue (which all expect that shape) still work from inside
// ListRows' cell slot, without ListView itself needing to know anything
// about Frappe doctypes.
const listViewColumns = computed(() =>
  visibleColumns.value.map((col) => ({
    key: col.fieldname,
    label: col.label,
    docField: col,
  })),
)

const listViewOptions = computed(() => ({
  selectable: true,
  showTooltip: false,
  getRowRoute: (row) => getRowRouteFor(row.name),
  emptyState: {
    title: hasActiveFilters.value ? 'No records match your filters' : 'No records yet',
    description: hasActiveFilters.value
      ? 'Try adjusting or clearing your filters.'
      : undefined,
    button: hasActiveFilters.value
      ? { label: 'Clear filters', variant: 'ghost', onClick: clearAllFilters }
      : { label: 'Create the first one', variant: 'outline', iconLeft: 'plus', onClick: goToNew },
  },
}))

// The mobile "Filter"/"Sort" pills open the same FilterEditor/SortEditor
// content as desktop's Popovers, just in a bottom sheet instead - see the
// template's isMobile branch. `rows` above is the one shared data source
// for both, so there's no separate mobile resource/normalization needed.
const showFilterSheet = ref(false)
const showSortSheet = ref(false)

// Row selection (desktop ListView only) - ListView owns the actual
// selection Set internally and emits update:selections, which this just
// mirrors as a plain name array for doBulkDelete to read. Tracked by
// name rather than index so it survives a re-fetch/reorder of allRows
// between selecting and acting on the selection.
const selectedNames = ref([])

// A filter/sort change replacing what's on screen makes the old
// selection meaningless - names that scroll out of view shouldn't stay
// silently selected for a bulk action the user can no longer see. Load
// More deliberately isn't included here (it only appends to allRows,
// via moreRows) - growing the list shouldn't wipe out a selection the
// user made before clicking it.
watch([listFilters, sortValue], () => {
  selectedNames.value = []
})

const showBulkDeleteConfirm = ref(false)
function confirmBulkDelete() {
  showBulkDeleteConfirm.value = true
}

async function doBulkDelete(close) {
  const names = selectedNames.value
  for (const name of names) {
    await rows.delete.submit({ name })
  }
  // rows.delete already removes a deleted row from useList's own
  // allData (see useList.ts's onSuccess -> listStore.removeRow), but
  // that only covers the first-page rows this instance owns - anything
  // pulled in via Load More lives in moreRows, a plain local array
  // rows.delete has no way to reach.
  moreRows.value = moreRows.value.filter((r) => !names.includes(r.name))
  selectedNames.value = []
  close()
  rows.fetch()
}

function formatValue(value, field) {
  if (value == null || value === '') return '-'
  if (field.fieldtype === 'Check') return value ? 'Yes' : 'No'
  return value
}

function isUserLink(field) {
  return field.fieldtype === 'Link' && field.options === 'User'
}

// Mobile card title - meta.title_field when the doctype declares one,
// else the record's own name/ID (see the template comment above the
// mobile card block for why this replaced visibleColumns[0]).
const titleFieldname = computed(() => metaResource.data?.title_field || null)
function cardTitle(row) {
  if (titleFieldname.value && row[titleFieldname.value]) return row[titleFieldname.value]
  return row.name
}

// Every in_list_view column except whichever one is already shown as the
// card's own title. titleFieldname covers the meta.title_field case
// directly; the value-based check below covers the (more common in this
// app) autoname: field:X case instead - e.g. AI Guide Section has no
// title_field, so cardTitle() falls back to row.name, but row.name and
// row.section_name are the exact same string there (confirmed live:
// autoname 'field:section_name'). Comparing by name.fieldname would mean
// parsing Frappe's various autoname syntaxes (field:x, prompt, hash,
// naming_series, a format string...); comparing by value instead sidesteps
// all of that and still reliably catches "this column would just repeat
// the title" for the field:X case specifically, which is the one that
// actually shows up here.
function cardBodyColumnsFor(row) {
  const title = cardTitle(row)
  return columns.value.filter((c) => c.fieldname !== titleFieldname.value && row[c.fieldname] !== title)
}

// A subtle left-border accent on the whole mobile card, colored by
// whichever status-like column happens to be showing on this list - lets a
// record's state read at a glance without hunting for the Status row
// inside the card. No accent (transparent) when the doctype has no
// status-like list column at all, rather than defaulting every card to
// the same color.
function cardAccentStyle(row) {
  const statusCol = visibleColumns.value.find((col) => isStatusLikeField(col))
  if (!statusCol || !row[statusCol.fieldname]) return {}
  return { borderLeft: `3px solid ${statusBorderColor(row[statusCol.fieldname])}` }
}

// Refresh re-runs the first page and drops anything loaded past it via
// Load More - a stale accumulated tail left in place after a refresh
// could silently mix pre- and post-refresh data together.
function refreshList() {
  moreRows.value = []
  hasExhaustedMore.value = false
  rows.reload()
  totalCountResource.fetch()
}

// Lightweight count-only query, same pattern as ConnectionsPanel.vue's
// own get_count usage - frappe.get_list's paged response has no total
// count without a dedicated call, and this is the one place on this page
// that actually needs one (the "X of Y" label).
const totalCountResource = useCall({
  url: '/api/v2/method/frappe.client.get_count',
  method: 'GET',
  params: () => ({ doctype: props.doctype, filters: JSON.stringify(listFilters.value) }),
  immediate: false,
})
watch(listFilters, () => totalCountResource.fetch(), { immediate: false })

// Doctypes reached via the generic /:doctypeRoute path use the shared
// DoctypeNew/DoctypeForm route names with a doctypeRoute param; doctypes
// with their own dedicated routes (e.g. Email Account, not tied to any
// App Module Setting module) use their own New/Form route names instead -
// derive which pattern applies from this list route's own name.
const isGenericRoute = route.name === 'DoctypeList'

function goToNew() {
  if (isGenericRoute) {
    router.push({ name: 'DoctypeNew', params: { doctypeRoute: route.params.doctypeRoute } })
  } else {
    router.push({ name: route.name.replace('List', 'New') })
  }
}

function goToRow(name) {
  router.push(getRowRouteFor(name))
}

// Same route goToRow above pushes, but as a route OBJECT rather than an
// imperative push - ListView's getRowRoute option renders each row as a
// router-link :to, so it needs the destination itself, not a function
// that navigates.
function getRowRouteFor(name) {
  if (isGenericRoute) {
    return { name: 'DoctypeForm', params: { doctypeRoute: route.params.doctypeRoute, name } }
  }
  return { name: route.name.replace('List', 'Form'), params: { name } }
}
</script>
