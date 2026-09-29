const numbers = {one:1,first:1,two:2,second:2,three:3,third:3,four:4,fourth:4,five:5,fifth:5,six:6,sixth:6,seven:7,seventh:7,eight:8,eighth:8,nine:9,ninth:9,ten:10,tenth:10};
function taskNumber(text, count) {
  const value = text.toLowerCase().replace(/^(?:the\s+)?(?:task\s+)?/, '').replace(/\s+task$/, '').trim();
  const number = value === 'last' ? count : numbers[value] ?? (/^\d+$/.test(value) ? Number(value) : NaN);
  if (!Number.isInteger(number) || number < 1 || number > count) throw new Error(`Choose a task number between 1 and ${count || 1}${count ? '.' : ', after adding a task.'}`);
  return number - 1;
}
export function parseCommand(transcript, tasks) {
  const text = transcript.trim().replace(/[.!?]+$/, '').trim();
  if (/^(?:read|read out|read aloud) (?:my |the )?(?:tasks|list)$/i.test(text)) return {type:'read'};
  const add = text.match(/^add(?: task)?\s+(.+)$/i);
  if (add) {
    if (add[1].length > 300) throw new Error('Please keep each task to 300 characters or fewer.');
    return {type:'add', title:add[1]};
  }
  const mark = text.match(/^mark (.+?) (complete|incomplete)$/i);
  const toggle = text.match(/^(complete|uncomplete|uncheck) (.+)$/i) || (mark && [mark[0],mark[2],mark[1]]);
  if (toggle) return {type:'complete', id:tasks[taskNumber(toggle[2],tasks.length)].id, completed:toggle[1].toLowerCase()==='complete'};
  const move = text.match(/^move (.+?) (up|down|to (?:the )?(?:top|bottom)|to (?:position |number )?(\w+))$/i);
  if (move) {
    const from = taskNumber(move[1],tasks.length);
    const direction = move[2].toLowerCase();
    const to = direction === 'up' ? from-1 : direction === 'down' ? from+1 : /top$/.test(direction) ? 0 : /bottom$/.test(direction) ? tasks.length-1 : taskNumber(move[3],tasks.length);
    if (to < 0 || to >= tasks.length || to === from) throw new Error('That task is already in that position.');
    const ids = tasks.map(task=>task.id);
    ids.splice(to,0,ids.splice(from,1)[0]);
    return {type:'move', ids};
  }
  throw new Error('Command not recognized. Try “add buy milk”, “complete task one”, “move task two up”, or “read my tasks”.');
}
