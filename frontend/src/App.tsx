import { useEffect, useState, useCallback } from 'react'
import { DndContext, DragOverlay, useDraggable, useDroppable } from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import type { ColumnMap, Task, TaskCreate, TaskUpdate } from './types'

const API = ''

/* ── Toast helper ── */

interface Toast {
  id: number
  message: string
  type: 'success' | 'error'
}

let toastId = 0

/* ── Icon components ── */

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className || 'w-4 h-4'}
    >
      <path
        fillRule="evenodd"
        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c-.84 0-1.673.025-2.5.075V3.75c0-.69.56-1.25 1.25-1.25h2.5c.69 0 1.25.56 1.25 1.25v.325C11.673 4.025 10.84 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
        clipRule="evenodd"
      />
    </svg>
  )
}

function PencilIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className || 'w-4 h-4'}
    >
      <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
    </svg>
  )
}

/* ── Component ── */

export default function App() {
  const [columns, setColumns] = useState<ColumnMap>({})
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [editTask, setEditTask] = useState<Task | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [activeTask, setActiveTask] = useState<Task | null>(null)

  const toast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  /* ── Fetch todo ── */

  const fetchTodo = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/todo`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setColumns(data.columns || {})
    } catch (err: any) {
      toast(err.message || 'Load error', 'error')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { fetchTodo() }, [fetchTodo])

  /* ── Create task ── */

  const handleCreate = async (data: TaskCreate) => {
    try {
      const res = await fetch(`${API}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const result = await res.json()
      setColumns(result.columns)
      toast('Task created')
      setShowAdd(false)
    } catch (err: any) {
      toast(err.message || 'Create error', 'error')
    }
  }

  /* ── Move / update task ── */

  const handleUpdate = async (taskId: string, update: TaskUpdate) => {
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update),
      })
      if (!res.ok) {
        if (res.status === 404) {
          toast('Task not found. Reloading...', 'error')
          fetchTodo()
          return
        }
        throw new Error(`HTTP ${res.status}`)
      }
      const result = await res.json()
      setColumns(result.columns)
      if (update.column === 'Done') toast('Task completed')
      else if (update.column) toast('Task moved')
    } catch (err: any) {
      toast(err.message || 'Update error', 'error')
    }
  }

  /* ── Delete task ── */

  const handleDelete = async (taskId: string) => {
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const result = await res.json()
      setColumns(result.columns)
      toast('Task deleted')
    } catch (err: any) {
      toast(err.message || 'Delete error', 'error')
    }
  }

  /* ── Drag handlers ── */

  const handleDragStart = useCallback((event: DragStartEvent) => {
    for (const tasks of Object.values(columns)) {
      const t = tasks.find(t => t.id === event.active.id)
      if (t) { setActiveTask(t); break }
    }
  }, [columns])

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setActiveTask(null)
    const { active, over } = event
    if (!over || active.id === over.id) return

    const taskId = active.id as string
    const targetColumn = over.id as string

    for (const [colName, tasks] of Object.entries(columns)) {
      if (tasks.some(t => t.id === taskId) && colName !== targetColumn) {
        handleUpdate(taskId, { column: targetColumn })
        break
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columns])

  /* ── Get aging badge style ── */

  const agingBadge = (days: number) => {
    if (days <= 1) return null
    const colors =
      days > 7 ? 'bg-red-900/50 text-red-400 border-red-800' :
      days > 3 ? 'bg-amber-900/50 text-amber-400 border-amber-800' :
                 'bg-zinc-800 text-zinc-400 border-zinc-700'
    return (
      <span className={`inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1.5 text-xs font-medium rounded border ${colors}`}>
        {days}d
      </span>
    )
  }

  /* ── Column order ── */

  const columnOrder = ['Backlog', 'Week', 'Today', 'Done']
  const orderedColumns = [
    ...columnOrder.filter(c => c in columns),
    ...Object.keys(columns).filter(c => !columnOrder.includes(c))
  ]

  /* ── Loading state ── */

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-zinc-500">Loading...</div>
      </div>
    )
  }

  /* ── Render ── */

  return (
    <div className="min-h-screen p-4 md:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Todo</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 transition-colors"
        >
          + New task
        </button>
      </header>

      {/* DnD Board */}
      <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {orderedColumns.map(colName => (
            <Column
              key={colName}
              name={colName}
              tasks={columns[colName] || []}
              onComplete={taskId => handleUpdate(taskId, { column: 'Done' })}
              onDelete={handleDelete}
              onUpdate={(taskId, update) => handleUpdate(taskId, update)}
              onEdit={(task) => setEditTask(task)}
              agingBadge={agingBadge}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null}>
          {activeTask ? (
            <div className="bg-zinc-900/90 rounded-lg border border-zinc-600 px-3 py-2.5 shadow-2xl rotate-2 opacity-90 max-w-[250px]">
              <p className="text-sm text-zinc-200">{activeTask.title}</p>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Empty state */}
      {orderedColumns.length === 0 && (
        <div className="text-center py-20 text-zinc-600">
          <p className="text-lg">No columns</p>
          <p className="text-sm mt-1">Add a task to get started</p>
        </div>
      )}

      {/* Add task dialog */}
      {showAdd && (
        <AddTaskDialog
          columns={orderedColumns}
          onSave={handleCreate}
          onClose={() => setShowAdd(false)}
        />
      )}

      {/* Edit task dialog */}
      {editTask && (
        <EditTaskDialog
          task={editTask}
          onSave={(title, note) => {
            handleUpdate(editTask.id, { title, note })
            setEditTask(null)
          }}
          onClose={() => setEditTask(null)}
        />
      )}

      {/* Toasts */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`toast-enter px-4 py-2 rounded-lg shadow-lg text-sm font-medium border ${
              t.type === 'success'
                ? 'bg-emerald-900/80 border-emerald-700 text-emerald-200'
                : 'bg-red-900/80 border-red-700 text-red-200'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════
   Column Component
   ═══════════════════════════════════════════ */

function Column({
  name, tasks, onComplete, onDelete, onUpdate, onEdit, agingBadge,
}: {
  name: string
  tasks: Task[]
  onComplete: (id: string) => void
  onDelete: (id: string) => void
  onUpdate: (id: string, u: TaskUpdate) => void
  onEdit: (task: Task) => void
  agingBadge: (days: number) => React.ReactNode
}) {
  const isToday = name === 'Today'
  const isDone = name === 'Done'

  // Droppable wrap — the Drop event uses column name as droppable id
  function DroppableColumn({ name, children, className: cn, ...rest }: { name: string; children: React.ReactNode; className?: string; [key: string]: any }) {
    const { setNodeRef, isOver } = useDroppable({ id: name })
    return (
      <div
        ref={setNodeRef}
        className={`bg-surface rounded-xl border ${isOver ? 'border-cyan-500/50 bg-cyan-950/20' : 'border-border'} p-3 min-h-[12rem] flex flex-col transition-colors ${cn || ''}`}
        {...rest}
      >
        {children}
      </div>
    )
  }

  return (
    <DroppableColumn name={name}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">{name}</h2>
        <span className="text-xs text-zinc-600 tabular-nums">{tasks.length}</span>
      </div>

      <div className="flex-1 space-y-2">
        {tasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            name={name}
            isToday={isToday}
            isDone={isDone}
            onComplete={() => onComplete(task.id)}
            onDelete={() => onDelete(task.id)}
            onTitleEdit={(title) => onUpdate(task.id, { title })}
            onEdit={() => onEdit(task)}
            agingBadge={agingBadge}
          />
        ))}

        {tasks.length === 0 && (
          <div className="text-center py-6 text-zinc-700 text-xs">
            Empty
          </div>
        )}
      </div>
    </DroppableColumn>
  )
}

/* ═══════════════════════════════════════════════════════
   DroppableColumn — DnD droppable zone wrapper
   ═══════════════════════════════════════════════════════ */

function DroppableColumn({ name, children, className: cn, ...rest }: { name: string; children: React.ReactNode; className?: string; [key: string]: any }) {
  const { setNodeRef, isOver } = useDroppable({ id: name })
  return (
    <div
      ref={setNodeRef}
      className={`bg-surface rounded-xl border ${isOver ? 'border-cyan-500/50 bg-cyan-950/20' : 'border-border'} p-3 min-h-[12rem] flex flex-col transition-colors ${cn || ''}`}
      {...rest}
    >
      {children}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════
   Task Card Component
   ═══════════════════════════════════════════════════════ */

function TaskCard({
  task, name, isToday, isDone, onComplete, onDelete, onTitleEdit, onEdit, agingBadge,
}: {
  task: Task
  name: string
  isToday: boolean
  isDone: boolean
  onComplete: () => void
  onDelete: () => void
  onTitleEdit: (title: string) => void
  onEdit: () => void
  agingBadge: (days: number) => React.ReactNode
}) {
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(task.title)

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    data: { name },
  })

  const handleSaveTitle = () => {
    if (editTitle.trim() && editTitle !== task.title) {
      onTitleEdit(editTitle.trim())
    }
    setEditing(false)
  }

  const stateIndicator = isDone ? (
    <span className="text-emerald-500 shrink-0 text-sm leading-none">&#10003;</span>
  ) : (
    <span className="text-zinc-500 shrink-0 text-sm leading-none">&#9744;</span>
  )

  return (
    <div
      ref={setNodeRef}
      style={transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined}
      className={`group relative bg-zinc-900/50 rounded-lg border border-zinc-800 px-3 py-2.5 hover:border-zinc-700 transition-colors ${isDragging ? 'opacity-30' : ''} cursor-grab active:cursor-grabbing`}
      {...listeners}
      {...attributes}
    >
      {/* Header row */}
      <div className="flex items-start gap-2">
        {/* State */}
        <button onClick={isDone ? undefined : onComplete} className="mt-0.5" title={isDone ? 'Completed' : 'Complete'}>
          {stateIndicator}
        </button>

        {/* Title + note */}
        <div className="flex-1 min-w-0">
          {editing ? (
            <input
              autoFocus
              value={editTitle}
              onChange={e => setEditTitle(e.target.value)}
              onBlur={handleSaveTitle}
              onKeyDown={e => { if (e.key === 'Enter') handleSaveTitle(); if (e.key === 'Escape') setEditing(false) }}
              className="w-full bg-zinc-800 text-sm text-zinc-200 px-2 py-0.5 rounded border border-zinc-600 outline-none"
            />
          ) : (
            <p
              className={`text-sm leading-snug cursor-text ${isDone ? 'line-through text-zinc-600' : 'text-zinc-200'}`}
              onClick={() => { setEditTitle(task.title); setEditing(true) }}
              title="Click to edit"
            >
              {task.title}
            </p>
          )}

          {/* Tags */}
          {task.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {task.tags.map(tag => (
                <span key={tag} className="text-[10px] font-medium text-indigo-400 bg-indigo-950/50 px-1.5 py-0.5 rounded">
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {/* Note preview */}
          {task.meta?.note && (
            <p className="text-[11px] text-zinc-500 mt-1 line-clamp-2">{task.meta.note}</p>
          )}
        </div>

        {/* Aging badge */}
        {isToday && agingBadge(task.aging_days)}
      </div>

      {/* Actions bar */}
      <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onEdit}
          className="text-zinc-500 hover:text-zinc-300 p-1 rounded hover:bg-zinc-800 transition-colors"
          title="Edit task"
        >
          <PencilIcon className="w-4 h-4" />
        </button>
        <button
          onClick={() => { if (confirm('Delete task?')) onDelete() }}
          className="text-zinc-500 hover:text-red-400 p-1 rounded hover:bg-zinc-800 transition-colors"
          title="Delete task"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════
   Add Task Dialog
   ═══════════════════════════════════════════ */

function AddTaskDialog({
  columns, onSave, onClose,
}: {
  columns: string[]
  onSave: (data: TaskCreate) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState('')
  const [column, setColumn] = useState(columns[0] || 'Backlog')
  const [tags, setTags] = useState('')
  const [note, setNote] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onSave({ title: title.trim(), column, tags: tags.trim(), note: note.trim() })
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-xl p-5 w-full max-w-md mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-sm font-medium text-zinc-200 mb-4">New task</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            autoFocus
            placeholder="Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 placeholder-zinc-500 outline-none focus:border-zinc-500 transition-colors"
          />
          <select
            value={column}
            onChange={e => setColumn(e.target.value)}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 outline-none focus:border-zinc-500 transition-colors"
          >
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input
            placeholder="Tags (e.g. #server #hogar)"
            value={tags}
            onChange={e => setTags(e.target.value)}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 placeholder-zinc-500 outline-none focus:border-zinc-500 transition-colors"
          />
          <textarea
            placeholder="Note (optional)"
            value={note}
            onChange={e => setNote(e.target.value)}
            rows={2}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 placeholder-zinc-500 outline-none focus:border-zinc-500 transition-colors resize-none"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="px-4 py-1.5 text-sm font-medium rounded-lg bg-zinc-200 text-zinc-900 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════
   Edit Task Dialog
   ═══════════════════════════════════════════ */

function EditTaskDialog({
  task, onSave, onClose,
}: {
  task: Task
  onSave: (title: string, note: string) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState(task.title)
  const [note, setNote] = useState(task.meta?.note || '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onSave(title.trim(), note.trim())
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-xl p-5 w-full max-w-md mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-sm font-medium text-zinc-200 mb-4">Edit task</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            autoFocus
            placeholder="Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 placeholder-zinc-500 outline-none focus:border-zinc-500 transition-colors"
          />
          <textarea
            placeholder="Description (optional)"
            value={note}
            onChange={e => setNote(e.target.value)}
            rows={4}
            className="w-full bg-zinc-800 text-sm text-zinc-200 px-3 py-2 rounded-lg border border-zinc-700 placeholder-zinc-500 outline-none focus:border-zinc-500 transition-colors resize-none"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="px-4 py-1.5 text-sm font-medium rounded-lg bg-zinc-200 text-zinc-900 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
