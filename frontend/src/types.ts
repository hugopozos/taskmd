export interface Task {
  id: string
  state: string
  title: string
  tags: string[]
  aging_days: number
  meta: Record<string, string>
}

export type ColumnMap = Record<string, Task[]>

export interface TodoResponse {
  columns: ColumnMap
}

export interface TaskCreate {
  title: string
  column?: string
  tags?: string
  note?: string
}

export interface TaskUpdate {
  column?: string
  title?: string
  tags?: string
  note?: string
}
