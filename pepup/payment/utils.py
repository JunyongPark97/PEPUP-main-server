
def groupbyseller(dict_ls):
    ret_ls = []
    store = {}
    helper = 0
    for d in dict_ls:
        if d['seller']['id'] in store.keys():
            store[d['seller']['id']]['products'] \
                .append({'trade_id': d['id'], 'product': d['product']})
            store[d['seller']['id']]['payinfo']['total'] += d['product']['discounted_price']

            helper += 1  # 한번 else 부터 갔다 들어오기 때문에 첫번째 들어왔을 때 뺴줌.
            if helper == 1:
                store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
                store[d['seller']['id']]['payinfo']['lack_volume'] -= 1

            if store[d['seller']['id']]['payinfo']['lack_amount'] > 0:  # 가격할인정책에서 남은 가격이 0원보다 클 때
                store[d['seller']['id']]['payinfo']['lack_amount'] -= d['product']['discounted_price']
            elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_amount']:
                store[d['seller']['id']]['payinfo']['delivery_charge'] = 0

            if store[d['seller']['id']]['payinfo']['lack_volume'] > 0:  # 수량할인정책에서 남은 개수가 0개보다 클 때
                store[d['seller']['id']]['payinfo']['lack_volume'] -= 1
            elif store[d['seller']['id']]['payinfo']['delivery_charge'] > 0 and d['payinfo']['active_volume']:
                store[d['seller']['id']]['payinfo']['delivery_charge'] = 0

        else:
            lack_amount = d['payinfo']['amount'] - d['product']['discounted_price']
            lack_volume = d['payinfo']['volume'] - 1

            if lack_amount <= 0 and d['payinfo']['active_amount']:
                delivery_charge = 0
            elif lack_volume <= 0 and d['payinfo']['active_volume']:
                delivery_charge = 0
            else:
                delivery_charge = d['payinfo']['general']
            mountain_delivery_charge = d['payinfo']['mountain']

            store[d['seller']['id']] = {
                'seller': d['seller'],
                'products': [{'trade_id': d['id'], 'product': d['product']}],
                'payinfo': {
                    'total': d['product']['discounted_price'],
                    'delivery_charge': delivery_charge,
                    'mountain_delivery_charge': mountain_delivery_charge,
                    'active_amount': d['payinfo']['active_amount'],
                    'active_volume': d['payinfo']['active_volume'],
                    'lack_amount': lack_amount,
                    'lack_volume': lack_volume
                }
            }
    for key in store:
        ret_ls.append(store[key])
    return ret_ls