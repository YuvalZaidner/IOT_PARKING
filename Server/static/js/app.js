const gridEl = document.getElementById('grid')
const closestEl = document.getElementById('closest')
const tsEl = document.getElementById('ts')
const arrivingIdEl = document.getElementById('arriving-id')

function render(spots, closest, freeCount){
  // Fixed 5 columns, rows 0..9
  const cols = [[],[],[],[],[]]
  for(let col=0; col<5; col++){
    for(let row=0; row<10; row++){
      const key = `${row},${col}`
      cols[col].push({row,col,key,info:spots[key]})
    }
  }

  gridEl.innerHTML=''
  cols.forEach(c=>{
    const colEl = document.createElement('div')
    colEl.className='col'
    // gate marker
    if(window._gate && window._gate.col === c[0].col){
      const g = document.createElement('div')
      g.className='gate'
      g.textContent = 'gate'
      colEl.appendChild(g)
    }else{
      // placeholder for alignment
      const ph = document.createElement('div')
      ph.style.height='30px'
      colEl.appendChild(ph)
    }

    c.forEach(s=>{
      const sp = document.createElement('div')
      const label = document.createElement('div')
      label.className = 'spot-label'
      sp.className='spot'
      // normalize status (be case-insensitive and robust to missing fields)
      let st = 'FREE'
      if(s.info){
        if(s.info.status) st = s.info.status
        else if(s.info.Status) st = s.info.Status
        else if(s.info.state) st = s.info.state
      }
  st = ('' + st).toUpperCase()
  if(st === 'FREE') sp.classList.add('free')
  else if(st === 'WAITING' || st === 'PENDING') sp.classList.add('waiting')
  else if(st === 'WRONG_PARK') sp.classList.add('wrong')
  else sp.classList.add('occupied')
      sp.textContent = `(${s.row},${s.col})`
      // small textual status under the tile
      // If the whole lot is full (freeCount===0) we hide the 'OCCUPIED' label to reduce clutter
      if(typeof freeCount !== 'undefined' && freeCount === 0 && st === 'OCCUPIED'){
        label.textContent = ''
      }else{
        label.textContent = st
      }
      label.style.marginTop = '6px'
      label.style.fontSize = '12px'
      label.style.fontWeight = '700'
      label.style.color = '#444'
      if(closest && closest===s.key){
        sp.style.outline='4px solid rgba(0,0,0,0.25)'
      }
      const wrapper = document.createElement('div')
      wrapper.style.display = 'flex'
      wrapper.style.flexDirection = 'column'
      wrapper.style.alignItems = 'center'
      wrapper.appendChild(sp)
      wrapper.appendChild(label)
      colEl.appendChild(wrapper)
    })
    gridEl.appendChild(colEl)
  })
}

async function poll(){
  try{
    const r = await fetch('/api/status')
    const j = await r.json()
  const spots = j.spots || {}
  const closest = j.closest_free
  const freeCount = typeof j.free_count !== 'undefined' ? j.free_count : null
  if(j.gate) window._gate = j.gate
  render(spots, closest, freeCount)
  // show parking full banner when DB reports no free spots
  const banner = document.getElementById('side-banner')
  if(banner){
    // Show a user-friendly message for both states
    if(typeof freeCount === 'number'){
      if(freeCount === 0){
        banner.textContent = 'THERE ARE NO FREE SPOTS'
        banner.style.background = '#ff3b2f' // bright red
        banner.style.color = '#000' // black text for contrast
        banner.style.display = 'flex'
        document.querySelector('.arriving-wrap').classList.add('square')
        banner.classList.add('square')
      }else{
        banner.textContent = 'THERE ARE FREE SPOTS'
        banner.style.background = '#7be36a' // bright green
        banner.style.color = '#000'
        banner.style.display = 'flex'
        document.querySelector('.arriving-wrap').classList.add('square')
        banner.classList.add('square')
      }
    }else{
      // fallback: use is_full if free_count not provided
      if(j.is_full){
        banner.textContent = 'THERE ARE NO FREE SPOTS'
        banner.style.background = '#ff3b2f'
        banner.style.color = '#000'
        banner.style.display = 'flex'
        document.querySelector('.arriving-wrap').classList.add('square')
        banner.classList.add('square')
      }else{
        banner.style.display = 'none'
        document.querySelector('.arriving-wrap').classList.remove('square')
        banner.classList.remove('square')
      }
    }
  }
  // display free_count in the right panel (optional)
  const metaEl = document.querySelector('.meta')
  if(metaEl && typeof j.free_count !== 'undefined'){
    metaEl.textContent = `Last update: ${new Date(j.ts).toLocaleTimeString()} — Free spots: ${j.free_count}`
  }
  const pill = document.getElementById('closest-pill')
  pill.textContent = closest ? `(${closest})` : '-'
      if(arrivingIdEl){
        const gid = j.gate_waiting_car || '-'
        // always set text (ensures UI shows current value even if we missed a transient)
        const prev = arrivingIdEl.textContent
        arrivingIdEl.textContent = gid
        // animate when id changes
        if(prev !== gid){
          arrivingIdEl.classList.remove('pulse')
          void arrivingIdEl.offsetWidth
          arrivingIdEl.classList.add('pulse')
        }
      }
    tsEl.textContent = new Date(j.ts).toLocaleTimeString()
  }catch(e){
    console.error(e)
  }
}
// poll faster so UI catches transient waiting states
setInterval(poll, 400)
poll()
