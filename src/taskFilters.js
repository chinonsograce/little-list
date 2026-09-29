export function localDate(date=new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}
export function isOverdue(task,today=localDate()) {return !task.completed && !!task.due_date && task.due_date<today;}
export function matchesTask(task,search,status,priority,today=localDate()) {
  return `${task.title}\n${task.notes || ''}`.toLowerCase().includes(search.trim().toLowerCase()) && (priority==='all' || task.priority===priority) && (status==='all' || status==='completed' && task.completed || status==='pending' && !task.completed || status==='overdue' && isOverdue(task,today));
}
