<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-medium text-gray-900 dark:text-gray-100">{{ pageTitle }}</h1>
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
      <!-- View controls, laid out like Frappe Helpdesk's list: quick filters on the
      left (a search box, then one inline control per filterable field), a thin
      divider, then Reload / Filter / Sort / Columns on the right. All frappe-ui.
      Phones keep just the search box plus icon-only actions. -->
      <div class="mb-4 flex items-center justify-between gap-2">
        <div class="quick-filters flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1">
          <div class="min-w-0 flex-1 sm:min-w-64 sm:max-w-xs sm:flex-none">
            <TextInput v-model="searchQuery" type="text" placeholder="Search records and their child table rows">
              <template #prefix>
                <FeatherIcon name="search" class="h-4 w-4 text-ink-gray-5" />
              </template>
            </TextInput>
          </div>
          <template v-if="!isMobile">
            <div v-for="field in quickFilterFields" :key="field.fieldname" class="min-w-36 flex-shrink-0">
              <FormControl
                v-if="field.fieldtype === 'Select'"
                type="select"
                class="[&_[data-slot=trigger]]:w-full"
                :options="[{ label: field.label, value: '' }, ...selectOptions(field)]"
                v-model="quickFilters[field.fieldname]"
              />
              <FormControl
                v-else-if="field.fieldtype === 'Check'"
                type="select"
                class="[&_[data-slot=trigger]]:w-full"
                :options="[{ label: field.label, value: '' }, { label: 'Yes', value: '1' }, { label: 'No', value: '0' }]"
                v-model="quickFilters[field.fieldname]"
              />
              <FormControl v-else type="text" :placeholder="field.label" v-model="quickFilters[field.fieldname]" />
            </div>
          </template>
        </div>

        <div v-if="!isMobile" class="h-5 flex-shrink-0 border-s border-outline-gray-2" />

        <div class="flex flex-shrink-0 items-center gap-2">
          <Button variant="outline" icon="refresh-cw" tooltip="Refresh" :loading="pageResource.loading" @click="refreshList" />

          <Dropdown v-if="canExport" :options="exportOptions" placement="bottom-end">
            <Button variant="outline" :icon-left="isMobile ? undefined : 'download'" :icon="isMobile ? 'download' : undefined" :loading="exporting" :tooltip="isMobile ? 'Export' : undefined">
              <template v-if="!isMobile">Export</template>
            </Button>
          </Dropdown>

          <template v-if="!isMobile">
            <Popover v-model:show="showFilterPopover" placement="bottom-end" popover-class="doctype-list-popover" :hide-on-blur="false">
              <template #target="{ togglePopover }">
                <Button variant="outline" icon-left="filter" label="Filter" data-toolbar-popover-trigger @click="togglePopover">
                  <template v-if="activeFilterCount" #suffix>
                    <span class="flex h-4 min-w-4 items-center justify-center rounded-full bg-surface-gray-7 px-1 text-2xs text-ink-white">
                      {{ activeFilterCount }}
                    </span>
                  </template>
                </Button>
              </template>
              <template #body-main>
                <div class="w-[26rem] max-w-[90vw] p-3">
                  <FilterEditor :fields="allFields" v-model="advancedFilters" />
                </div>
              </template>
            </Popover>

            <SortControl v-model="sortValue" v-model:show="showSortPopover" :fields="allFields" />
          </template>

          <template v-else>
            <span class="relative inline-flex">
              <Button variant="outline" icon="filter" tooltip="Filter" @click="showFilterSheet = true" />
              <span
                v-if="activeFilterCount"
                class="pointer-events-none absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-surface-gray-7 px-1 text-2xs text-ink-white"
              >
                {{ activeFilterCount }}
              </span>
            </span>
            <Button variant="outline" icon="sliders" tooltip="Sort" @click="showSortSheet = true" />
          </template>

          <ColumnPicker v-model:show="showColumnsPopover" :prefs="columnPrefs" locked-label="ID" :compact="isMobile" />
        </div>
      </div>

      <Dialog v-model="showFilterSheet" :options="{ size: 'sm', title: 'filter-sheet' }">
        <template #body>
          <div class="filter-sheet-panel flex flex-col">
            <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800">
              <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Filter</h3>
              <Button variant="ghost" size="sm" icon="x" tooltip="Close" @click="showFilterSheet = false" />
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
              <FilterEditor :fields="allFields" v-model="advancedFilters" @update:model-value="showFilterSheet = false" />
            </div>
            <div class="flex flex-shrink-0 justify-end border-t px-4 py-3 dark:border-gray-800">
              <Button icon-left="x" @click="showFilterSheet = false" size="sm">Close</Button>
            </div>
          </div>
        </template>
      </Dialog>

      <Dialog v-model="showSortSheet" :options="{ size: 'sm', title: 'sort-sheet' }">
        <template #body>
          <div class="filter-sheet-panel flex flex-col">
            <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800">
              <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Sort</h3>
              <Button variant="ghost" size="sm" icon="x" tooltip="Close" @click="showSortSheet = false" />
            </div>
            <div class="px-4 py-4">
              <SortEditor :fields="allFields" v-model="sortValue" />
            </div>
            <div class="flex justify-end gap-2 border-t px-4 py-3 dark:border-gray-800">
              <Button icon-left="x" @click="showSortSheet = false" size="sm">Close</Button>
              <Button variant="solid" icon-left="check" @click="showSortSheet = false" size="sm">Done</Button>
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

      <div v-if="pageResource.loading && !pageResource.data" class="space-y-2">
        <Skeleton v-for="i in 5" :key="i" height="2.5rem" />
      </div>
      <ErrorMessage v-else-if="listError" :message="listError" />
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
          class="cursor-pointer overflow-hidden rounded-xl border bg-white p-3.5 shadow-sm transition-shadow active:shadow-none dark:border-gray-800 dark:bg-gray-900"
          :style="cardAccentStyle(row)"
          @click="goToRow(row.name)"
        >
          <!-- Header: the record ID (always first) on the left, status
          badge + chevron on the right. -->
          <div class="flex items-center justify-between gap-2">
            <span class="max-w-[60%] truncate rounded-md bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">
              {{ row.name }}
            </span>
            <div class="flex items-center gap-1.5">
              <span
                v-if="cardStatusColumn && row[cardStatusColumn.fieldname]"
                class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                :class="statusBadgeClasses(row[cardStatusColumn.fieldname])"
              >
                {{ row[cardStatusColumn.fieldname] }}
              </span>
              <FeatherIcon name="chevron-right" class="h-4 w-4 flex-shrink-0 text-gray-300 dark:text-gray-600" />
            </div>
          </div>
          <!-- Title only when it says something the ID doesn't (a
          title_field, or a value that differs from the ID). -->
          <div
            v-if="cardTitle(row) !== row.name"
            class="mt-2 truncate text-base font-semibold text-gray-900 dark:text-gray-100"
          >
            {{ cardTitle(row) }}
          </div>
          <dl v-if="cardBodyColumnsFor(row).length" class="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-2.5">
            <div v-for="col in cardBodyColumnsFor(row)" :key="col.fieldname" class="min-w-0">
              <dt class="truncate text-xs text-gray-400 dark:text-gray-500">{{ col.label }}</dt>
              <dd class="truncate text-base text-gray-800 dark:text-gray-200">
                <UserLinkHoverCard v-if="isUserLink(col) && row[col.fieldname]" :user="row[col.fieldname]" @click.stop>
                  <span class="underline decoration-dotted">{{ row[col.fieldname] }}</span>
                </UserLinkHoverCard>
                <template v-else>{{ formatValue(row[col.fieldname], col) || '-' }}</template>
              </dd>
            </div>
          </dl>
          <p v-if="row.modified" class="mt-2.5 text-xs text-ink-gray-5" :title="fullDatetime(row.modified)">
            Updated {{ timeAgo(row.modified) }}{{ timeAgo(row.modified) === 'now' ? '' : ' ago' }}
          </p>
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
      <div v-if="!isMobile" class="doctype-list-scroll mt-1" @scroll.passive="onListScroll">
      <ListView
        :key="gridKey"
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
            <span
              v-else-if="column.key === 'modified'"
              class="truncate text-base text-ink-gray-6"
              :title="fullDatetime(row.modified)"
            >
              {{ timeAgo(row.modified) }}
            </span>
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
          <SelectionBar v-if="selectable" @delete="confirmBulkDelete" />
        </template>
      </ListView>
      </div>

      <!-- Row count, Load More and the page-size choice. The list above scrolls inside its own box, so the
      page itself does not grow with the number of rows. -->
      <ListFooter
        v-if="showResults"
        class="mt-3"
        :model-value="pageSize"
        :options="{ rowCount: allRows.length, totalCount: totalCountResource.data ?? 0, pageLengthOptions: PAGE_SIZE_OPTIONS }"
        @update:model-value="setPageSize"
      >
        <!-- frappe-ui's own Load More button renders empty here, so the right-hand side is drawn in full -->
        <template #right>
          <div class="flex items-center">
            <Button v-if="canLoadMore" variant="outline" size="sm" :loading="moreResource.loading" @click="loadMore">Load More</Button>
            <div v-if="canLoadMore" class="mx-3 h-5 border-s border-outline-gray-2" />
            <div class="flex items-center gap-1 text-base text-ink-gray-5">
              <div>{{ allRows.length }}</div>
              <div>of</div>
              <div>{{ totalCountResource.data ?? 0 }}</div>
            </div>
          </div>
        </template>
      </ListFooter>
    </template>
  </AppLayout>
</template>

<style>
/* The desktop list is about 15 rows tall: more rows scroll inside this box, not the whole page, and the
column headings stay in view. (Header 2.5rem + 15 rows of 2.57rem.) */
.doctype-list-scroll {
  max-height: 41rem;
  overflow: auto;
  overscroll-behavior: contain;
}
/* The list's own inner wrappers scroll too, which would stop the heading from sticking to this box */
.doctype-list-scroll > .relative.overflow-x-auto,
.doctype-list-scroll .flex.w-max.min-w-full {
  overflow: visible !important;
}
.doctype-list-scroll .mb-2.grid.rounded.bg-surface-gray-2 {
  position: sticky;
  top: 0;
  z-index: 5;
}

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
/* frappe-ui's dialog wrapper is a column flex box centred with
justify-content, so the sheet is pinned to the bottom edge with
justify-content: flex-end (align-items would only move it sideways). */
[data-dialog='filter-sheet'].dialog-overlay > div,
[data-dialog='sort-sheet'].dialog-overlay > div {
  justify-content: flex-end;
  padding: 0;
}
[data-dialog='filter-sheet'] .dialog-content,
[data-dialog='sort-sheet'] .dialog-content {
  margin: 0;
  max-width: none;
  width: 100vw;
  border-radius: 1rem 1rem 0 0;
  padding-bottom: env(safe-area-inset-bottom);
  animation: list-sheet-up 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes list-sheet-up {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  [data-dialog='filter-sheet'] .dialog-content,
  [data-dialog='sort-sheet'] .dialog-content {
    animation: none;
  }
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { breakpointsTailwind, useBreakpoints, watchDebounced } from '@vueuse/core'
import {
  useCall,
  Dropdown,
  call,
  Button,
  TextInput,
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
  ListFooter,
  Popover,
  Tooltip,
} from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import UserLinkHoverCard from '@/components/UserLinkHoverCard.vue'
import FilterEditor from '@/components/FilterEditor.vue'
import SortEditor from '@/components/SortEditor.vue'
import SelectionBar from '@/components/SelectionBar.vue'
import { exportRecords as downloadRecords } from '@/utils/exportRecords'
import ColumnPicker from '@/components/ColumnPicker.vue'
import SortControl from '@/components/SortControl.vue'
import { useColumnPrefs } from '@/composables/useColumnPrefs'
import Skeleton from '@/components/Skeleton.vue'
import { useMeta, useListFields, useFormFields } from '@/data/useMeta'
import { findModuleByRoute } from '@/data/modules'
import { linkTitle, isTitledLink, ensureTitlesForRows } from '@/data/linkTitles'
import { setPageTitle } from '@/data/pageTitle'
import { timeAgo, fullDatetime } from '@/utils/time'
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
// Columns arrangement (order, headings, added/removed fields) from the shared
// Columns picker - see composables/useColumnPrefs.js. Default = the doctype's
// own list-view fields.
const columnPrefs = useColumnPrefs({
  storageKey: `janadhikara-list-columns-${props.doctype}`,
  allFields,
  defaultColumns: columns,
})
const visibleColumns = columnPrefs.visibleColumns

// Everything the list must fetch: the record ID, the default in_list_view
// fields (mobile cards always show those) and whatever extra columns the
// user picked.
const fetchFields = computed(() => {
  const names = new Set(['name', 'modified'])
  columns.value.forEach((c) => names.add(c.fieldname))
  visibleColumns.value.forEach((c) => names.add(c.fieldname))
  return [...names]
})

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
// Opened from the Dashboard (or any link) with ?filters={...} in Frappe's filter shape.
function filtersFromRoute() {
  try {
    const parsed = route.query.filters ? JSON.parse(route.query.filters) : null
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}
advancedFilters.value = filtersFromRoute()
watch(() => route.query.filters, () => { advancedFilters.value = filtersFromRoute() })
const searchQuery = ref('')

function selectOptions(field) {
  return (field.options || '')
    .split('\n')
    .map((v) => v.trim())
    .filter(Boolean)
    .map((v) => ({ label: v, value: v }))
}

// Fields offered as inline quick filters in the toolbar, as in Helpdesk: the
// doctype's own "standard filter" fields (up to three), or - if it flags none -
// its first few list columns.
const QUICK_FILTER_FIELDTYPES = new Set(['Select', 'Check', 'Data', 'Link', 'Small Text', 'Phone', 'Int', 'Float'])
const quickFilterFields = computed(() => {
  const flagged = allFields.value.filter((f) => f.in_standard_filter && QUICK_FILTER_FIELDTYPES.has(f.fieldtype))
  const pool = flagged.length ? flagged : columns.value.filter((f) => QUICK_FILTER_FIELDTYPES.has(f.fieldtype))
  return pool.slice(0, 3)
})

const quickFilterEntries = computed(() => {
  const result = {}
  for (const field of quickFilterFields.value) {
    const value = quickFilters[field.fieldname]
    if (value == null || value === '') continue
    if (field.fieldtype === 'Check') {
      result[field.fieldname] = Number(value)
    } else if (field.fieldtype === 'Select') {
      result[field.fieldname] = value
    } else {
      result[field.fieldname] = ['like', `%${value}%`]
    }
  }
  return result
})

// searchQuery goes last and wins on `name` if advancedFilters also
// happens to target it (unlikely in practice, but the same
// last-one-wins precedence quickFilters -> advancedFilters already uses
// above, just extended one step further).
// Search runs server-side (janadhikara.api.search_record_names) so it can
// look past the list's own columns - at the ID, the title, every text-like
// field and the rows of child tables - and returns the matching record
// names, which then filter the list. While a search is still in flight
// (debounced), a plain ID `like` keeps the list responsive.
const searchNames = ref(null)
watchDebounced(
  searchQuery,
  async (q) => {
    const text = q.trim()
    if (!text) {
      searchNames.value = null
      return
    }
    try {
      const result = await call('janadhikara.api.search_record_names', { doctype: props.doctype, txt: text })
      // Ignore a stale answer if the box changed while this was in flight.
      if (searchQuery.value.trim() === text) searchNames.value = Array.isArray(result) ? result : result?.message || []
    } catch {
      searchNames.value = null
    }
  },
  { debounce: 300 },
)
const searchFilter = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return {}
  if (searchNames.value) return { name: ['in', searchNames.value.length ? searchNames.value : ['\u0000none']] }
  return { name: ['like', `%${q}%`] }
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

// The list shows `pageSize` rows to start with; Load More adds the next `pageSize`, and the list scrolls
// inside its own box (see the template). Choosing another page size starts the list again from the top
// with that many rows. A change of filters, sort or doctype also starts again.
const PAGE_SIZE_OPTIONS = [15, 30, 50, 100]
const pageSize = ref(15)
const moreRows = ref([])
const noMoreRows = ref(false)
function listParams(start) {
  return {
    fields: JSON.stringify(fetchFields.value),
    filters: JSON.stringify(listFilters.value),
    order_by: `${sortValue.value.field} ${sortValue.value.direction}`,
    start,
    limit: pageSize.value,
  }
}
const pageResource = useCall({
  url: `/api/v2/document/${props.doctype}`,
  method: 'GET',
  params: () => listParams(0),
  immediate: false,
})
const moreResource = useCall({
  url: `/api/v2/document/${props.doctype}`,
  method: 'GET',
  params: () => listParams((pageResource.data?.length || 0) + moreRows.value.length),
  immediate: false,
})

let lastLoadKey = ''
// `force` (Refresh, after a delete) fetches even when nothing about the request changed
function loadPage(force = false) {
  if (!metaResource.data || !fetchFields.value.length) return
  const key = JSON.stringify([fetchFields.value, listFilters.value, sortValue.value, pageSize.value, props.doctype])
  if (!force && key === lastLoadKey) return
  lastLoadKey = key
  moreRows.value = []
  noMoreRows.value = false
  pageResource.fetch()
}
watch(
  () => [JSON.stringify(fetchFields.value), JSON.stringify(listFilters.value), sortValue.value.field, sortValue.value.direction, pageSize.value, props.doctype, !!metaResource.data],
  () => loadPage(),
  { immediate: true },
)

const canLoadMore = computed(() => !noMoreRows.value && allRows.value.length < (totalCountResource.data ?? 0))
// Reaching the bottom of the list's own scroll box brings in the next rows
function onListScroll(event) {
  const box = event.target
  if (box.scrollTop + box.clientHeight >= box.scrollHeight - 80) loadMore()
}

async function loadMore() {
  if (moreResource.loading || pageResource.loading || !canLoadMore.value) return
  const key = lastLoadKey
  const next = (await moreResource.fetch()) || []
  if (key !== lastLoadKey) return // the list was started again (filters, sort, page size) while this was loading
  const have = new Set(allRows.value.map((r) => r.name))
  moreRows.value = [...moreRows.value, ...next.filter((r) => !have.has(r.name))]
  if (next.length < pageSize.value || allRows.value.length >= (totalCountResource.data ?? Infinity)) noMoreRows.value = true
}
function setPageSize(size) {
  pageSize.value = size
}

const allRows = computed(() => [...(pageResource.data || []), ...moreRows.value])
// An aborted request (a newer one replaced it) is not an error worth showing
const listError = computed(() => {
  const error = pageResource.error
  return error && !/abort/i.test(String(error?.message || error)) ? error : null
})

// The mobile card view and the desktop table (template, below) each open
// their own `v-if` rather than chaining `v-else-if` off the loading/error/
// empty block above them, since they're structurally different elements
// (a plain list wrapper vs. a table) - that split previously let a
// transient rows.error (e.g. an aborted in-flight request) render its
// message ABOVE the table while the table kept rendering underneath it,
// instead of the error replacing the table the way the v-if chain above
// it implies. Both blocks gate on this single flag instead.
const showResults = computed(() => !pageResource.loading && !listError.value && allRows.value.length > 0)

// ListView's own column shape ({key, label, ...}) doesn't carry Frappe
// field metadata (fieldtype, options, ...) - docField keeps the original
// field object attached per column so isStatusLikeField/isUserLink/
// formatValue (which all expect that shape) still work from inside
// ListRows' cell slot, without ListView itself needing to know anything
// about Frappe doctypes.
// The record ID is always the first column - it's what links, exports and
// support conversations refer to, and isn't a field the picker can hide.
const ID_COLUMN = { fieldname: 'name', label: 'ID', fieldtype: 'Data' }
// ...and "Last Modified" is always the last one: when each record was last
// updated, shown as a relative time (the exact moment on hover).
const MODIFIED_COLUMN = { fieldname: 'modified', label: 'Last Modified', fieldtype: 'Datetime' }
// Column width follows the data: the longest of the heading and the loaded cells (capped), in rem.
function columnWidth(col) {
  if (col.fieldname === 'modified') return '6.5rem'
  let longest = String(col.label || '').length + 2
  for (const row of allRows.value) {
    const text = col.fieldname === 'modified' ? '10mo' : String(formatValue(row[col.fieldname], col) ?? '')
    if (text.length > longest) longest = text.length
  }
  // At least this wide, and spare room is shared out in proportion (Last Modified stays fixed).
  const rem = Math.min(Math.max(longest * 0.5 + 1.5, 5), 15).toFixed(1)
  return `minmax(${rem}rem, ${rem}fr)`
}
const listViewColumns = computed(() =>
  [ID_COLUMN, ...visibleColumns.value.filter((c) => c.fieldname !== 'name' && c.fieldname !== 'modified'), MODIFIED_COLUMN].map((col) => ({
    key: col.fieldname,
    label: col.label,
    width: columnWidth(col),
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
// Filter and Sort popovers ignore frappe-ui's own outside-click handling
// (:hide-on-blur="false") because the editors inside open dropdowns that render
// in a portal outside the popover - treating a click on one of those options as
// "outside" closed the popover before the option registered. So they're
// controlled here and closed by this pointerdown listener, which skips clicks
// inside the popover, inside any such nested dropdown, and on the toolbar
// buttons themselves (their own click already toggles).
const showFilterPopover = ref(false)
const showSortPopover = ref(false)
const showColumnsPopover = ref(false)
function closeToolbarPopoversOnOutsideClick(event) {
  if (!showFilterPopover.value && !showSortPopover.value && !showColumnsPopover.value) return
  const target = event.target
  if (!(target instanceof Element)) return
  if (
    target.closest(
      '.doctype-list-popover, [data-reka-popper-content-wrapper], [data-slot="content"], [data-toolbar-popover-trigger]',
    )
  )
    return
  showFilterPopover.value = false
  showSortPopover.value = false
  showColumnsPopover.value = false
}
// Only one of the two open at a time.
watch(showFilterPopover, (open) => { if (open) { showSortPopover.value = false; showColumnsPopover.value = false } })
watch(showSortPopover, (open) => { if (open) { showFilterPopover.value = false; showColumnsPopover.value = false } })
watch(showColumnsPopover, (open) => { if (open) { showFilterPopover.value = false; showSortPopover.value = false } })
onMounted(() => document.addEventListener('pointerdown', closeToolbarPopoversOnOutsideClick, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeToolbarPopoversOnOutsideClick, true))

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
// ListView keeps its own copy of the ticked rows (it drives the "N selected"
// banner) and can't be reset from outside - so wherever this list clears its
// selection, bumping gridKey remounts the grid with a clean one too.
const gridKey = ref(0)
watch([listFilters, sortValue, pageSize], () => {
  selectedNames.value = []
  gridKey.value++
})

const showBulkDeleteConfirm = ref(false)
function confirmBulkDelete() {
  showBulkDeleteConfirm.value = true
}

async function doBulkDelete(close) {
  const names = selectedNames.value
  for (const name of names) {
    await call('frappe.client.delete', { doctype: props.doctype, name })
  }
  selectedNames.value = []
  gridKey.value++
  close()
  loadPage(true)
  totalCountResource.fetch()
}

function formatValue(value, field) {
  if (value == null || value === '') return '-'
  if (field.fieldtype === 'Check') return value ? 'Yes' : 'No'
  // A linked record shows by its title (name), not its ID.
  if (isTitledLink(field)) return linkTitle(field.options, value)
  return value
}

// Fetch the titles for every Link column on the rows currently loaded
// (desktop table, mobile cards and the card title all read them back
// through formatValue / linkTitle).
watch(
  () => [allRows.value, columns.value, visibleColumns.value],
  () => ensureTitlesForRows(allRows.value, [...columns.value, ...visibleColumns.value]),
  { immediate: true },
)

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
// The first status-like column is shown as a badge in the card header
// instead, so it's left out of the body grid.
const cardStatusColumn = computed(() => columns.value.find((c) => isStatusLikeField(c)) || null)
function cardBodyColumnsFor(row) {
  const title = cardTitle(row)
  return visibleColumns.value.filter(
    (c) =>
      c.fieldname !== titleFieldname.value &&
      c.fieldname !== cardStatusColumn.value?.fieldname &&
      row[c.fieldname] !== title,
  )
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
  loadPage(true)
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

// Export: every record matching the filters and search (not only this page), with every field.
// Offered only to users who hold Frappe's Export permission for this doctype.
const canExportResource = useCall({
  url: '/api/v2/method/janadhikara.dashboard.can_export',
  method: 'GET',
  params: () => ({ doctype: props.doctype }),
})
const canExport = computed(() => !!canExportResource.data)
const exporting = ref(false)
async function runExport(format) {
  exporting.value = true
  await downloadRecords({
    doctype: props.doctype,
    filters: listFilters.value,
    fields: 'all',
    orderBy: `${sortValue.value.field} ${sortValue.value.direction}`,
    format,
    total: totalCountResource.data,
  })
  exporting.value = false
}
const exportOptions = [
  { label: 'CSV (.csv)', icon: 'file-text', onClick: () => runExport('csv') },
  { label: 'Excel (.xlsx)', icon: 'grid', onClick: () => runExport('xlsx') },
]

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
